"""Pipeline-backed implementation of ``ResponsesSupportCompleteWithReferences``.

Uses the OpenAI proxy (``get_async_openai_client``) to stream Responses API
events, folds them through the handler pipeline, and optionally persists the
final normalized text + references via ``Message.modify_async`` at the end.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx
import unique_sdk
from openai import AsyncOpenAI

from unique_toolkit.framework_utilities.openai.client import get_async_openai_client
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    chunks_to_sdk_references,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses_pipeline import (
    ResponsesStreamPipeline,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import LanguageModelMessages
from unique_toolkit.protocols.support import ResponsesSupportCompleteWithReferences

if TYPE_CHECKING:
    from openai.types.responses import (
        ResponseIncludable,
        ResponseInputItemParam,
        ResponseInputParam,
        ResponseOutputItem,
        ResponseTextConfigParam,
        ToolParam,
        response_create_params,
    )
    from openai.types.shared_params import Metadata, Reasoning

    from unique_toolkit.app.unique_settings import UniqueSettings
    from unique_toolkit.content.schemas import ContentChunk
    from unique_toolkit.language_model.schemas import (
        LanguageModelMessageOptions,
        LanguageModelToolDescription,
        ResponsesLanguageModelStreamResponse,
    )

from unique_toolkit.chat.responses_api import (
    _convert_language_model_message_to_openai_responses_api,
    _convert_messages_to_openai,
)

_LOGGER = logging.getLogger(__name__)


def _convert_tools(
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None,
) -> list[ToolParam] | None:
    if not tools:
        return None
    from unique_toolkit.chat.responses_api import _convert_tools_to_openai

    return _convert_tools_to_openai(tools)


class ResponsesCompleteWithReferences(ResponsesSupportCompleteWithReferences):
    """``ResponsesSupportCompleteWithReferences`` backed by the handler pipeline.

    Creates a ``ResponsesStreamPipeline`` with typed handlers for text deltas,
    tool calls, the completed event, and code interpreter lifecycle, then
    consumes the stream and builds the final result.
    """

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        pipeline: ResponsesStreamPipeline,
        client: AsyncOpenAI | None = None,
        additional_headers: dict[str, str] | None = None,
    ) -> None:
        self._settings = settings
        self._pipeline = pipeline
        self._client = client or get_async_openai_client(
            unique_settings=settings,
            additional_headers=additional_headers,
        )

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

        def input_messages(
            messages: str
            | LanguageModelMessages
            | Sequence[ResponseInputItemParam | LanguageModelMessageOptions],
        ) -> ResponseInputParam | str:
            if isinstance(messages, str):
                return messages

            if isinstance(messages, LanguageModelMessages):
                return _convert_messages_to_openai(messages.root)

            converted_messages: list[ResponseInputItemParam] = []

            for message in messages:
                if isinstance(message, LanguageModelMessageOptions):
                    converted_messages.append(
                        _convert_language_model_message_to_openai_responses_api(message)
                    )
                else:
                    converted_messages.append(message)

            return converted_messages

        # TODO: Talk to Ahmed about this
        converted_messages = input_messages(messages)  # type: ignore

        converted_tools = _convert_tools(tools)

        # -- Mark message as streaming ---------------------------------------
        await unique_sdk.Message.modify_async(
            id=chat.last_assistant_message_id,
            chatId=chat.chat_id,
            user_id=settings.context.auth.user_id.get_secret_value(),
            company_id=settings.context.auth.company_id.get_secret_value(),
            references=chunks_to_sdk_references(content_chunks or []),
            startedStreamingAt=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),  # type: ignore
        )

        self._pipeline.reset()
        try:
            create_kwargs: dict = {}
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

            stream = await self._client.responses.create(
                model=model,
                input=converted_messages,
                stream=True,
                temperature=temperature,
                **create_kwargs,
            )
            async for event in stream:
                await self._pipeline.on_event(event)
        except httpx.RemoteProtocolError as exc:
            _LOGGER.warning(
                "Stream connection closed prematurely (incomplete chunked read). "
                "Finalizing with content received so far. Error: %s",
                exc,
            )
        finally:
            await self._pipeline.on_stream_end()

        return self._pipeline.build_result(
            message_id=chat.last_assistant_message_id,
            chat_id=chat.chat_id,
            created_at=datetime.now(timezone.utc),
        )
