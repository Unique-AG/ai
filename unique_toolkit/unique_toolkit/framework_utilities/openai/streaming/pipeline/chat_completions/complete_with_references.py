"""Pipeline-backed implementation of ``SupportCompleteWithReferences`` for Chat Completions.

The orchestrator owns the :data:`StreamEvent` bus and the default
:class:`MessagePersistingSubscriber`. Handlers/pipelines stay pure — all
``unique_sdk.Message.modify_async`` calls happen in the subscriber
reacting to :class:`StreamStarted` / :class:`TextDelta` / :class:`StreamEnded`.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import httpx
from openai import AsyncOpenAI

from unique_toolkit.framework_utilities.openai.client import get_async_openai_client
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelToolDescription,
)
from unique_toolkit.protocols.support import SupportCompleteWithReferences

from ..events import StreamEnded, StreamEventBus, StreamStarted, TextDelta
from ..subscribers import MessagePersistingSubscriber
from .stream_pipeline import ChatCompletionStreamPipeline

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletionMessageParam,
        ChatCompletionToolChoiceOptionParam,
    )

    from unique_toolkit.app.unique_settings import UniqueSettings
    from unique_toolkit.content.schemas import ContentChunk
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


class ChatCompletionsCompleteWithReferences(SupportCompleteWithReferences):
    """``SupportCompleteWithReferences`` backed by the Chat Completions handler pipeline.

    Wiring:

    * Handlers/pipeline accumulate state only (pure).
    * This orchestrator owns a :class:`StreamEventBus`.
    * A default :class:`MessagePersistingSubscriber` is registered on the
      bus in ``__init__`` to handle ``Message.modify_async`` calls and
      reference filtering. Callers that want additional subscribers (logging,
      analytics, ...) can pass a pre-configured bus.
    """

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        pipeline: ChatCompletionStreamPipeline,
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
        # Register the default message persister. Callers who pass a custom
        # bus have already decided their subscriber set and we do not add to it.
        if bus is None:
            self._bus.subscribe(MessagePersistingSubscriber(settings).handle)

    @property
    def bus(self) -> StreamEventBus:
        """Expose the bus so callers can attach additional subscribers."""
        return self._bus

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

        message_id = chat.last_assistant_message_id
        chat_id = chat.chat_id

        self._pipeline.reset()
        await self._bus.publish_and_wait_async(
            StreamStarted(
                message_id=message_id,
                chat_id=chat_id,
                content_chunks=tuple(content_chunks or ()),
            )
        )

        try:
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

            stream = await self._client.chat.completions.create(
                model=model,
                messages=converted_messages,
                stream=True,
                temperature=temperature,
                **optional_create_kwargs,
            )

            index = 0
            async for chunk in stream:
                flushed = await self._pipeline.on_event(chunk, index=index)
                index += 1
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
