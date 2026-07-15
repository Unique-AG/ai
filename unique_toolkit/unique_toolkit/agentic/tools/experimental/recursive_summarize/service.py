from __future__ import annotations

import logging
import math
import re
from typing import cast

from unique_toolkit import LanguageModelMessages
from unique_toolkit._common.token.token_counting import (
    num_token_for_language_model_messages,
)
from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.tools.experimental.recursive_summarize.config import (
    RecursiveSummarizeConfig,
)
from unique_toolkit.agentic.tools.experimental.recursive_summarize.prompts import (
    MAP_SYSTEM_PROMPT,
    MAP_USER_TEMPLATE,
    REDUCE_SYSTEM_PROMPT,
    REDUCE_USER_TEMPLATE,
)
from unique_toolkit.app import run_async_tasks_parallel
from unique_toolkit.language_model import LanguageModelService

logger = logging.getLogger(__name__)


class RecursiveSummarizerService:
    """Recursive map-reduce summarizer for documents exceeding a single context window."""

    def __init__(
        self,
        language_model_service: LanguageModelService,
        config: RecursiveSummarizeConfig,
    ) -> None:
        self.language_model_service = language_model_service
        self.config = config

    async def summarize(
        self,
        chunks: list[str],
        task_description: str,
    ) -> str:
        if not chunks:
            return "No text content found in documents for summarization."

        if self.config.language_model is None:
            raise ValueError("RecursiveSummarize language_model is not configured.")

        if self.config.model_max_input_tokens <= 0:
            raise ValueError(
                "RecursiveSummarize model_max_input_tokens is not configured."
            )

        return await self._summarize_recursively(
            chunks=chunks,
            task_description=task_description,
            level=1,
            use_reduce_template=False,
        )

    async def _summarize_recursively(
        self,
        chunks: list[str],
        task_description: str,
        level: int,
        use_reduce_template: bool,
    ) -> str:
        if level > self.config.max_recursion_levels:
            raise RuntimeError(
                f"Recursive summarization exceeded max_recursion_levels="
                f"{self.config.max_recursion_levels}"
            )

        if use_reduce_template:
            system_prompt = REDUCE_SYSTEM_PROMPT
            user_template = REDUCE_USER_TEMPLATE
        else:
            system_prompt = MAP_SYSTEM_PROMPT
            user_template = MAP_USER_TEMPLATE

        input_budget = self._compute_input_budget(
            task_description=task_description,
            system_prompt=system_prompt,
            user_template=user_template,
        )
        prepared_chunks = self._prepare_chunks(chunks, input_budget)
        message_batches = self._pack_chunks_into_batches(
            chunks=prepared_chunks,
            task_description=task_description,
            input_budget=input_budget,
            system_prompt=system_prompt,
            user_template=user_template,
        )

        if not message_batches:
            return ""

        if len(message_batches) == 1:
            return await self._summarize_messages(message_batches[0])

        summary_tasks = [self._summarize_messages(batch) for batch in message_batches]
        summary_results = await run_async_tasks_parallel(
            tasks=summary_tasks,
            max_tasks=self.config.num_workers,
        )

        summary_texts: list[str] = []
        for idx, result in enumerate(summary_results):
            if isinstance(result, Exception):
                logger.error(
                    "Error summarizing section %d/%d: %s",
                    idx + 1,
                    len(summary_results),
                    result,
                )
                raise result
            if isinstance(result, str):
                summary_texts.append(result)
            else:
                raise RuntimeError(f"Unexpected result type: {type(result)}")

        return await self._summarize_recursively(
            chunks=summary_texts,
            task_description=task_description,
            level=level + 1,
            use_reduce_template=True,
        )

    def _compute_input_budget(
        self,
        task_description: str,
        system_prompt: str,
        user_template: str,
    ) -> int:
        prompt_overhead = self._measure_prompt_overhead(
            task_description=task_description,
            system_prompt=system_prompt,
            user_template=user_template,
        )
        max_output = self.config.model_max_output_tokens
        reserved_output = (
            min(self.config.output_reservation_tokens, max_output)
            if max_output > 0
            else self.config.output_reservation_tokens
        )
        raw_budget = (
            math.floor(
                self.config.model_max_input_tokens * self.config.token_safety_factor
            )
            - prompt_overhead
            - reserved_output
        )
        return max(raw_budget, 256)

    def _measure_prompt_overhead(
        self,
        task_description: str,
        system_prompt: str,
        user_template: str,
    ) -> int:
        messages = self._compose_messages(
            task_description=task_description,
            content_text="",
            system_prompt=system_prompt,
            user_template=user_template,
        )
        encoder = self.config.language_model.get_encoder()
        return num_token_for_language_model_messages(messages=messages, encode=encoder)

    def _prepare_chunks(self, chunks: list[str], input_budget: int) -> list[str]:
        encode = self.config.language_model.get_encoder()
        max_content_tokens = max(input_budget, 64)
        decode = self.config.language_model.get_decoder()
        prepared: list[str] = []
        for chunk in chunks:
            if not chunk.strip():
                continue
            token_count = len(encode(chunk))
            if token_count <= max_content_tokens:
                prepared.append(chunk)
            else:
                prepared.extend(
                    self._sub_split_text(chunk, encode, decode, max_content_tokens)
                )
        return prepared

    @staticmethod
    def _sub_split_text(
        text: str,
        encode,
        decode,
        max_content_tokens: int,
    ) -> list[str]:
        tokens = encode(text)
        parts: list[str] = []
        for start in range(0, len(tokens), max_content_tokens):
            parts.append(decode(tokens[start : start + max_content_tokens]))
        return parts

    def _pack_chunks_into_batches(
        self,
        chunks: list[str],
        task_description: str,
        input_budget: int,
        system_prompt: str,
        user_template: str,
    ) -> list[LanguageModelMessages]:
        if not chunks:
            return []

        encoder = self.config.language_model.get_encoder()

        message_batches: list[LanguageModelMessages] = []
        current_batch: list[str] = []
        for chunk in chunks:
            candidate_messages = self._compose_messages(
                task_description=task_description,
                content_text="\n".join(current_batch + [chunk]),
                system_prompt=system_prompt,
                user_template=user_template,
            )
            candidate_count = num_token_for_language_model_messages(
                messages=candidate_messages,
                encode=encoder,
            )

            if candidate_count <= input_budget:
                current_batch.append(chunk)
                continue

            if current_batch:
                message_batches.append(
                    self._compose_messages(
                        task_description=task_description,
                        content_text="\n".join(current_batch),
                        system_prompt=system_prompt,
                        user_template=user_template,
                    )
                )
                current_batch = [chunk]
            else:
                message_batches.append(
                    self._compose_messages(
                        task_description=task_description,
                        content_text=chunk,
                        system_prompt=system_prompt,
                        user_template=user_template,
                    )
                )
                current_batch = []

        if current_batch:
            message_batches.append(
                self._compose_messages(
                    task_description=task_description,
                    content_text="\n".join(current_batch),
                    system_prompt=system_prompt,
                    user_template=user_template,
                )
            )

        return message_batches

    def _compose_messages(
        self,
        task_description: str,
        content_text: str,
        system_prompt: str,
        user_template: str,
    ) -> LanguageModelMessages:
        user_content = render_template(
            user_template,
            task_description=task_description,
            document_text=content_text,
        )
        builder = LanguageModelMessages([]).builder()
        builder.system_message_append(content=system_prompt.strip())
        builder.user_message_append(content=user_content)
        return builder.build()

    async def _summarize_messages(
        self,
        prepared_summary_messages: LanguageModelMessages,
    ) -> str:
        response = await self.language_model_service.complete_async(
            messages=prepared_summary_messages,
            model_name=self.config.language_model.name,
            other_options={"max_tokens": self.config.output_reservation_tokens},
        )

        if (
            not response
            or not response.choices
            or not response.choices[0].message.content
        ):
            error_message = "Language model returned empty response"
            logger.error(error_message)
            raise RuntimeError(error_message)

        return _strip_markdown_code_fence(
            cast(str, response.choices[0].message.content)
        )


_MARKDOWN_FENCE_PATTERN = re.compile(
    r"^\s*```(?:markdown|md)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


def _strip_markdown_code_fence(text: str) -> str:
    match = _MARKDOWN_FENCE_PATTERN.match(text.strip())
    if match is not None:
        return match.group(1).strip()
    return text.strip()
