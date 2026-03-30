"""Unique SDK streaming events for :class:`ChatCompletionChunk` streams."""

from __future__ import annotations

from typing import TYPE_CHECKING

import unique_sdk

from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
    chunks_to_sdk_references,
)

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

    from unique_toolkit.app.unique_settings import UniqueSettings
    from unique_toolkit.content.schemas import ContentChunk
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.chat_completion_accumulator import (
        ChatCompletionStreamAccumulator,
    )


class ChatCompletionSdkPersistence:
    """Applies replacers, emits ``Message.create_event_async`` for each delta, and
    optionally persists the final normalized text + references via ``Message.modify_async``
    at the end of the stream.

    The *accumulator* is the authoritative source of the original (pre-replacer) text;
    this class only tracks the normalized text produced after applying replacers.
    """

    def __init__(
        self,
        unique_settings: UniqueSettings,
        *,
        accumulator: ChatCompletionStreamAccumulator,
        replacers: list[StreamingReplacerProtocol],
        content_chunks: list[ContentChunk] | None = None,
        resolve_references: bool = False,
        send_every_n_events: int = 1,
    ) -> None:
        if unique_settings.context.chat is None:
            raise ValueError("Chat context is required")

        self._settings = unique_settings
        self._accumulator = accumulator
        self._replacers = replacers
        self._content_chunks = content_chunks
        self._resolve_references = resolve_references
        self._send_every_n_events = max(1, send_every_n_events)
        self._full_text = ""

    @property
    def full_text(self) -> str:
        """Normalized text accumulated across the stream (after replacers)."""
        return self._full_text

    def reset(self) -> None:
        self._accumulator.reset()
        self._full_text = ""

    async def on_event(
        self,
        event: ChatCompletionChunk,
        *,
        index: int,
    ) -> None:
        if len(event.choices) == 0 or self._settings.context.chat is None:
            return

        delta = event.choices[0].delta.content or ""
        for replacer in self._replacers:
            delta = replacer.process(delta)

        self._full_text += delta

        if (index + 1) % self._send_every_n_events == 0:
            await self._emit_message_event()

    async def on_stream_end(self) -> None:
        # Cascade flush: each replacer's flush output is fed into the next replacer's
        # process() before that replacer is itself flushed.  This ensures the pattern
        # replacer's buffered tail reaches downstream replacers before they finalise.
        remaining = ""
        for replacer in self._replacers:
            if remaining:
                remaining = replacer.process(remaining)
            remaining += replacer.flush()
        if remaining:
            self._full_text += remaining
            await self._emit_message_event()

        if self._resolve_references and self._settings.context.chat is not None:
            await self._persist_final_message()

    async def _persist_final_message(self) -> None:
        """Write normalized text and references to the platform via ``Message.modify_async``."""
        chat = self._settings.context.chat
        assert chat is not None
        await unique_sdk.Message.modify_async(
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            id=chat.last_assistant_message_id,
            chatId=chat.chat_id,
            text=self._full_text or None,
            references=chunks_to_sdk_references(self._content_chunks or []),
        )

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
                originalText=self._accumulator.full_text,
            ),
        )
