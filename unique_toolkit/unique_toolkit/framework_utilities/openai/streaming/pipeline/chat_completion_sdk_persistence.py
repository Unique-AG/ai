"""Unique SDK streaming events for :class:`ChatCompletionChunk` streams."""

from __future__ import annotations

import copy

import unique_sdk
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)


class ChatCompletionSdkPersistence:
    """Applies replacers and emits ``Message.create_event_async`` for chat completion deltas."""

    def __init__(
        self,
        unique_settings: UniqueSettings,
        *,
        replacers: list[StreamingReplacerProtocol],
        send_every_n_events: int = 1,
    ) -> None:
        if unique_settings.context.chat is None:
            raise ValueError("Chat context is required")

        self._settings = unique_settings
        self._replacers = replacers
        self._send_every_n_events = max(1, send_every_n_events)
        self._original_text = ""
        self._full_text = ""

    def reset(self) -> None:
        self._original_text = ""
        self._full_text = ""

    async def on_event(
        self,
        event: ChatCompletionChunk,
        *,
        index: int,
    ) -> None:
        if len(event.choices) == 0 or self._settings.context.chat is None:
            return

        self._original_text += copy.deepcopy(event.choices[0].delta.content) or ""

        delta = event.choices[0].delta.content or ""
        for replacer in self._replacers:
            delta = replacer.process(delta)

        self._full_text += delta

        if (index + 1) % self._send_every_n_events == 0:
            await self._emit_message_event()

    async def on_stream_end(self) -> None:
        return

    async def _emit_message_event(self) -> None:
        chat = self._settings.context.chat
        assert chat is not None
        await unique_sdk.Message.create_event_async(
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            **unique_sdk.Message.CreateEventParams(
                chatId=chat.chat_id,
                messageId=chat.last_assistant_message_id,
                text=self._full_text,
                originalText=self._original_text,
            ),
        )
