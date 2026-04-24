"""Pipeline-backed implementation of ``ResponsesSupportCompleteWithReferences``.

The orchestrator owns the :data:`StreamEvent` bus and the default
:class:`MessagePersistingSubscriber`. Handlers/pipelines stay pure — all
``unique_sdk.Message.modify_async`` calls happen in the subscriber reacting
to :class:`StreamStarted` / :class:`TextDelta` / :class:`StreamEnded`.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, TypeGuard

import httpx
from openai import AsyncOpenAI

from unique_toolkit.framework_utilities.openai.client import get_async_openai_client
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageOptions,
    LanguageModelMessages,
)
from unique_toolkit.protocols.support import ResponsesSupportCompleteWithReferences

from ..events import StreamEnded, StreamEventBus, StreamStarted, TextDelta
from ..subscribers import MessagePersistingSubscriber
from .stream_pipeline import ResponsesStreamPipeline

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
        LanguageModelToolDescription,
        ResponsesLanguageModelStreamResponse,
    )

from unique_toolkit.chat.responses_api import (
    _convert_messages_to_openai,
)

_LOGGER = logging.getLogger(__name__)


def _is_language_model_messages(
    msgs: "list[LanguageModelMessageOptions] | list[ResponseInputItemParam]",
) -> TypeGuard[list[LanguageModelMessageOptions]]:
    """Narrow a union of message lists to LanguageModelMessageOptions."""
    return len(msgs) > 0 and isinstance(msgs[0], LanguageModelMessageOptions)


def _is_response_input_items(
    msgs: "list[LanguageModelMessageOptions] | list[ResponseInputItemParam]",
) -> TypeGuard[list[ResponseInputItemParam]]:
    """Narrow a union of message lists to ResponseInputItemParam (TypedDicts)."""
    return len(msgs) > 0 and isinstance(msgs[0], dict)


def _convert_tools(
    tools: Sequence[LanguageModelToolDescription | ToolParam] | None,
) -> list[ToolParam] | None:
    if not tools:
        return None
    from unique_toolkit.chat.responses_api import _convert_tools_to_openai

    return _convert_tools_to_openai(tools)


class ResponsesCompleteWithReferences(ResponsesSupportCompleteWithReferences):
    """``ResponsesSupportCompleteWithReferences`` backed by the handler pipeline.

    Wiring mirrors :class:`ChatCompletionsCompleteWithReferences`: a default
    :class:`MessagePersistingSubscriber` is registered on an owned
    :class:`StreamEventBus`; callers can pass a pre-configured bus to
    replace or augment the subscriber set.
    """

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        pipeline: ResponsesStreamPipeline,
        client: AsyncOpenAI | None = None,
        additional_headers: dict[str, str] | None = None,
        bus: StreamEventBus | None = None,
    ) -> None:
        self._settings = settings
        self._pipeline = pipeline
        self._client = client or get_async_openai_client(
            unique_settings=settings,
            additional_headers=additional_headers,
        )
        self._bus: StreamEventBus = bus if bus is not None else StreamEventBus()
        if bus is None:
            self._bus.subscribe(MessagePersistingSubscriber(settings).handle)

    @property
    def bus(self) -> StreamEventBus:
        """Expose the bus so callers can attach additional subscribers."""
        return self._bus

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
            model_name.value
            if isinstance(model_name, LanguageModelName)
            else model_name
        )

        message_id = chat.last_assistant_message_id
        chat_id = chat.chat_id

        # -- Build the OpenAI request ----------------------------------------

        def input_messages(
            messages: str
            | LanguageModelMessages
            | list[LanguageModelMessageOptions]
            | list[ResponseInputItemParam],
        ) -> ResponseInputParam | str:
            if isinstance(messages, str):
                return messages

            if isinstance(messages, LanguageModelMessages):
                return _convert_messages_to_openai(messages.root)

            if len(messages) == 0:
                return []

            converted_messages: list[ResponseInputItemParam] = []
            if _is_language_model_messages(messages):
                for message in messages:
                    converted_messages.append(message.to_openai(mode="responses"))
                return converted_messages

            if _is_response_input_items(messages):
                for message in messages:
                    converted_messages.append(message)
                return converted_messages

            return converted_messages

        # TODO(UN-15891): confirm Responses input shape for mixed message types
        converted_messages = input_messages(messages)  # type: ignore

        converted_tools = _convert_tools(tools)

        self._pipeline.reset()
        await self._bus.publish_and_wait_async(
            StreamStarted(
                message_id=message_id,
                chat_id=chat_id,
                content_chunks=tuple(content_chunks or ()),
            )
        )

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
                flushed = await self._pipeline.on_event(event)
                if flushed:
                    await self._publish_text_delta(message_id, chat_id)
        except httpx.RemoteProtocolError as exc:
            _LOGGER.warning(
                "Stream connection closed prematurely (incomplete chunked read). "
                "Finalizing with content received so far. Error: %s",
                exc,
            )
        finally:
            flushed = await self._pipeline.on_stream_end()
            if flushed:
                await self._publish_text_delta(message_id, chat_id)
            text_state = self._pipeline.get_text()
            await self._bus.publish_and_wait_async(
                StreamEnded(
                    message_id=message_id,
                    chat_id=chat_id,
                    full_text=text_state.full_text,
                    original_text=text_state.original_text,
                )
            )

        return self._pipeline.build_result(
            message_id=message_id,
            chat_id=chat_id,
            created_at=datetime.now(timezone.utc),
        )

    async def _publish_text_delta(self, message_id: str, chat_id: str) -> None:
        text_state = self._pipeline.get_text()
        await self._bus.publish_and_wait_async(
            TextDelta(
                message_id=message_id,
                chat_id=chat_id,
                full_text=text_state.full_text,
                original_text=text_state.original_text,
            )
        )
