"""Pipeline-backed implementation of ``SupportCompleteWithReferences`` for Chat Completions.

Uses the OpenAI proxy (``get_async_openai_client``) to stream Chat Completions
events, folds them through the handler pipeline, and optionally persists the
final normalized text + references via ``Message.modify_async`` at the end.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import httpx
import unique_sdk

from unique_toolkit.framework_utilities.openai.client import get_async_openai_client
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    NORMALIZATION_MAX_MATCH_LENGTH,
    NORMALIZATION_PATTERNS,
    StreamingPatternReplacer,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completion_pipeline import (
    ChatCompletionStreamPipeline,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completion_text_handler import (
    ChatCompletionTextHandler,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completion_tool_call_handler import (
    ChatCompletionToolCallHandler,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelToolDescription,
)
from unique_toolkit.protocols.support import SupportCompleteWithReferences

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletionMessageParam,
        ChatCompletionToolChoiceOptionParam,
    )

    from unique_toolkit.app.unique_settings import UniqueSettings
    from unique_toolkit.content.schemas import ContentChunk
    from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
        NormalizationPattern,
        StreamingReplacerProtocol,
    )
    from unique_toolkit.language_model.schemas import (
        LanguageModelStreamResponse,
        LanguageModelTool,
    )

_LOGGER = logging.getLogger(__name__)


def _convert_messages(
    messages: LanguageModelMessages | list[ChatCompletionMessageParam],
) -> list[ChatCompletionMessageParam]:
    if isinstance(messages, LanguageModelMessages):
        return messages.model_dump(exclude_none=True, by_alias=False)
    return list(messages)


def _convert_tools(
    tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None,
) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    result = []
    for tool in tools:
        if isinstance(tool, LanguageModelToolDescription):
            result.append(tool.to_openai(mode="completions"))
        else:
            result.append(
                {"type": "function", "function": tool.model_dump(exclude_none=True)}
            )
    return result or None


class PipelineChatCompletionsStreamingHandler(SupportCompleteWithReferences):
    """``SupportCompleteWithReferences`` backed by the Chat Completions handler pipeline.

    Creates a ``ChatCompletionStreamPipeline`` with typed handlers for text
    content and tool calls, then consumes the stream and builds the final result.
    """

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        normalization_patterns: list[NormalizationPattern] = NORMALIZATION_PATTERNS,
        max_match_length: int = NORMALIZATION_MAX_MATCH_LENGTH,
        resolve_references: bool = True,
        send_every_n_events: int = 1,
        extra_replacers: Sequence[StreamingReplacerProtocol] | None = None,
        additional_headers: dict[str, str] | None = None,
    ) -> None:
        self._settings = settings
        self._normalization_patterns = normalization_patterns
        self._max_match_length = max_match_length
        self._resolve_references = resolve_references
        self._send_every_n_events = send_every_n_events
        self._extra_replacers = extra_replacers
        self._additional_headers = additional_headers

    def complete_with_references(
        self,
        messages: LanguageModelMessages,
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict | None = None,
        temperature: float = 0.0,
        timeout: int = 240_000,
        tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None = None,
        start_text: str | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        other_options: dict | None = None,
    ) -> LanguageModelStreamResponse:
        return asyncio.get_event_loop().run_until_complete(
            self.complete_with_references_async(
                messages=messages,
                model_name=model_name,
                content_chunks=content_chunks,
                debug_info=debug_info,
                temperature=temperature,
                timeout=timeout,
                tools=tools,
                start_text=start_text,
                tool_choice=tool_choice,
                other_options=other_options,
            )
        )

    async def complete_with_references_async(
        self,
        messages: LanguageModelMessages | list[ChatCompletionMessageParam],
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict | None = None,
        temperature: float = 0.0,
        timeout: int = 240_000,
        tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        start_text: str | None = None,
        other_options: dict | None = None,
    ) -> LanguageModelStreamResponse:
        settings = self._settings
        chat = settings.context.chat
        if chat is None:
            raise ValueError("Chat context is not set")

        model: str = (
            model_name.value
            if isinstance(model_name, LanguageModelName)
            else model_name
        )

        # -- Mark message as streaming ---------------------------------------
        await unique_sdk.Message.modify_async(
            id=chat.last_assistant_message_id,
            chatId=chat.chat_id,
            user_id=settings.context.auth.user_id.get_secret_value(),
            company_id=settings.context.auth.company_id.get_secret_value(),
            startedStreamingAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore
        )

        # -- Build replacer chain --------------------------------------------
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

        # -- Build pipeline --------------------------------------------------
        pipeline = ChatCompletionStreamPipeline(
            text_handler=ChatCompletionTextHandler(
                settings,
                replacers=replacers,
                content_chunks=content_chunks,
                resolve_references=self._resolve_references,
                send_every_n_events=self._send_every_n_events,
            ),
            tool_call_handler=ChatCompletionToolCallHandler(),
        )

        client = get_async_openai_client(
            unique_settings=settings,
            additional_headers=self._additional_headers,
        )

        pipeline.reset()

        try:
            # -- Convert messages and tools to OpenAI format ----------------------
            converted_messages = _convert_messages(messages)
            converted_tools = _convert_tools(tools)

            optional_create_kwargs: dict[str, Any] = {}
            if converted_tools:
                optional_create_kwargs["tools"] = converted_tools
            if tool_choice is not None:
                optional_create_kwargs["tool_choice"] = tool_choice
            if other_options:
                for k, v in other_options.items():
                    optional_create_kwargs.setdefault(k, v)

            # -- Stream the completion --------------------------------------------
            stream = await client.chat.completions.create(
                model=model,
                messages=converted_messages,
                stream=True,
                temperature=temperature,
                **optional_create_kwargs,
            )

            index = 0
            async for chunk in stream:
                await pipeline.on_event(chunk, index=index)
                index += 1
        except httpx.RemoteProtocolError as exc:
            _LOGGER.warning(
                "Stream connection closed prematurely (incomplete chunked read). "
                "Finalizing with content received so far. Error: %s",
                exc,
            )
        finally:
            await pipeline.on_stream_end()

        return pipeline.build_result(
            message_id=chat.last_assistant_message_id,
            chat_id=chat.chat_id,
            created_at=datetime.now(timezone.utc),
        )
