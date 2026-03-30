"""Pipeline-backed implementation of ``ResponsesSupportCompleteWithReferences``.

Uses the OpenAI proxy (``get_async_openai_client``) to stream Responses API
events, folds them through the pipeline (accumulator + SDK persistence), and
runs post-stream reference resolution when configured.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone

import httpx
import unique_sdk
from openai.types.responses import (
    ResponseIncludable,
    ResponseInputItemParam,
    ResponseOutputItem,
    ResponseTextConfigParam,
    ToolParam,
    response_create_params,
)
from openai.types.shared_params import Metadata, Reasoning

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.framework_utilities.openai.client import get_async_openai_client
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    NORMALIZATION_MAX_MATCH_LENGTH,
    NORMALIZATION_PATTERNS,
    NormalizationPattern,
    StreamingPatternReplacer,
    StreamingReplacerProtocol,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses_accumulator import (
    ResponsesStreamAccumulator,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses_sdk_persistence import (
    ResponsesSdkPersistence,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.reference import add_references_to_message
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageOptions,
    LanguageModelMessages,
    LanguageModelToolDescription,
    ResponsesLanguageModelStreamResponse,
)
from unique_toolkit.protocols.support import ResponsesSupportCompleteWithReferences

_LOGGER = logging.getLogger(__name__)


def _convert_messages(
    messages: str
    | LanguageModelMessages
    | Sequence[
        ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
    ],
) -> (
    str
    | Sequence[
        ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
    ]
):
    """Normalise the union of accepted message types into what the SDK expects."""
    if isinstance(messages, str):
        return messages
    from unique_toolkit.chat.responses_api import _convert_messages_to_openai

    seq: Sequence[
        ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
    ] = messages.root if isinstance(messages, LanguageModelMessages) else messages
    return _convert_messages_to_openai(seq)


def _convert_tools(
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None,
) -> list[ToolParam] | None:
    if not tools:
        return None
    from unique_toolkit.chat.responses_api import _convert_tools_to_openai

    return _convert_tools_to_openai(tools)


class PipelineResponsesStreamingHandler(ResponsesSupportCompleteWithReferences):
    """``ResponsesSupportCompleteWithReferences`` backed by the streaming pipeline.

    Instead of delegating to ``unique_sdk.Integrated.responses_stream_async``
    (server-side streaming), this handler calls the OpenAI Responses API
    directly via the proxy, folds the stream through
    ``ResponsesStreamAccumulator`` + ``ResponsesSdkPersistence``, and runs
    client-side reference resolution when configured.
    """

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        normalization_patterns: list[NormalizationPattern] = NORMALIZATION_PATTERNS,
        max_match_length: int = NORMALIZATION_MAX_MATCH_LENGTH,
        resolve_references: bool = True,
        extra_replacers: Sequence[StreamingReplacerProtocol] | None = None,
        additional_headers: dict[str, str] | None = None,
    ) -> None:
        self._settings = settings
        self._normalization_patterns = normalization_patterns
        self._max_match_length = max_match_length
        self._resolve_references = resolve_references
        self._extra_replacers = extra_replacers
        self._additional_headers = additional_headers

    def complete_with_references(  # noqa: PLR0913
        self,
        *,
        model_name: LanguageModelName | str,
        messages: str
        | LanguageModelMessages
        | Sequence[
            ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
        ],
        content_chunks: list[ContentChunk] | None = None,
        tools: Sequence[LanguageModelToolDescription | ToolParam] | None = None,
        temperature: float = 0.0,
        debug_info: dict | None = None,
        start_text: str | None = None,
        include: list[ResponseIncludable] | None = None,
        instructions: str | None = None,
        max_output_tokens: int | None = None,
        metadata: Metadata | None = None,
        parallel_tool_calls: bool | None = None,
        text: ResponseTextConfigParam | None = None,
        tool_choice: response_create_params.ToolChoice | None = None,
        top_p: float | None = None,
        reasoning: Reasoning | None = None,
        other_options: dict | None = None,
    ) -> ResponsesLanguageModelStreamResponse:
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.complete_with_references_async(
                model_name=model_name,
                messages=messages,
                content_chunks=content_chunks,
                tools=tools,
                temperature=temperature,
                debug_info=debug_info,
                start_text=start_text,
                include=include,
                instructions=instructions,
                max_output_tokens=max_output_tokens,
                metadata=metadata,
                parallel_tool_calls=parallel_tool_calls,
                text=text,
                tool_choice=tool_choice,
                top_p=top_p,
                reasoning=reasoning,
                other_options=other_options,
            )
        )

    async def complete_with_references_async(  # noqa: PLR0913
        self,
        *,
        model_name: LanguageModelName | str,
        messages: str
        | LanguageModelMessages
        | Sequence[
            ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
        ],
        content_chunks: list[ContentChunk] | None = None,
        tools: Sequence[LanguageModelToolDescription | ToolParam] | None = None,
        temperature: float = 0.0,
        debug_info: dict | None = None,
        start_text: str | None = None,
        include: list[ResponseIncludable] | None = None,
        instructions: str | None = None,
        max_output_tokens: int | None = None,
        metadata: Metadata | None = None,
        parallel_tool_calls: bool | None = None,
        text: ResponseTextConfigParam | None = None,
        tool_choice: response_create_params.ToolChoice | None = None,
        top_p: float | None = None,
        reasoning: Reasoning | None = None,
        other_options: dict | None = None,
    ) -> ResponsesLanguageModelStreamResponse:
        settings = self._settings
        chat = settings.context.chat
        if chat is None:
            raise ValueError("Chat context is not set")

        model: str = (
            model_name.name if isinstance(model_name, LanguageModelName) else model_name
        )

        # -- Build the OpenAI request ----------------------------------------
        converted_messages = _convert_messages(messages)
        converted_tools = _convert_tools(tools)

        create_kwargs: dict = {
            "model": model,
            "input": converted_messages,
            "stream": True,
            "temperature": temperature,
        }
        if converted_tools:
            create_kwargs["tools"] = converted_tools
        if instructions is not None:
            create_kwargs["instructions"] = instructions
        if include is not None:
            create_kwargs["include"] = include
        if max_output_tokens is not None:
            create_kwargs["max_output_tokens"] = max_output_tokens
        if metadata is not None:
            create_kwargs["metadata"] = metadata
        if parallel_tool_calls is not None:
            create_kwargs["parallel_tool_calls"] = parallel_tool_calls
        if text is not None:
            create_kwargs["text"] = text
        if tool_choice is not None:
            create_kwargs["tool_choice"] = tool_choice
        if top_p is not None:
            create_kwargs["top_p"] = top_p
        if reasoning is not None:
            create_kwargs["reasoning"] = reasoning
        if other_options:
            for k, v in other_options.items():
                create_kwargs.setdefault(k, v)

        # -- Mark message as streaming ---------------------------------------
        await unique_sdk.Message.modify_async(
            id=chat.last_assistant_message_id,
            chatId=chat.chat_id,
            user_id=settings.context.auth.user_id.get_secret_value(),
            company_id=settings.context.auth.company_id.get_secret_value(),
            startedStreamingAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore
        )

        # -- Stream through the pipeline -------------------------------------
        replacers: list[StreamingReplacerProtocol] = []
        if self._normalization_patterns:
            replacers.append(
                StreamingPatternReplacer(
                    self._normalization_patterns,
                    max_match_length=self._max_match_length,
                )
            )
        if self._extra_replacers:
            replacers.extend(self._extra_replacers)

        accumulator = ResponsesStreamAccumulator()
        persistence = ResponsesSdkPersistence(settings, replacers=replacers)

        client = get_async_openai_client(
            unique_settings=settings,
            additional_headers=self._additional_headers,
        )

        accumulator.reset()
        persistence.reset()

        try:
            stream = await client.responses.create(**create_kwargs)
            index = 0
            async for event in stream:
                accumulator.apply(event)
                await persistence.on_event(event, index=index)
                index += 1
            await persistence.on_stream_end()
        except httpx.RemoteProtocolError as exc:
            _LOGGER.warning(
                "Stream connection closed prematurely (incomplete chunked read). "
                "Finalizing with content received so far. Error: %s",
                exc,
            )

        result = accumulator.build_responses_stream_result(
            message_id=chat.last_assistant_message_id,
            chat_id=chat.chat_id,
            created_at=datetime.now(timezone.utc),
        )

        # -- Post-stream reference resolution --------------------------------
        if self._resolve_references and content_chunks:
            result.message, _ = add_references_to_message(
                result.message,
                search_context=content_chunks,
                model=model,
            )

        return result
