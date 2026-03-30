"""Handler for ``ResponseTextDeltaEvent`` — accumulates text, applies replacers, emits SDK events."""

from __future__ import annotations

from typing import TYPE_CHECKING

import unique_sdk

from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
    chunks_to_sdk_references,
)

if TYPE_CHECKING:
    from openai.types.responses import ResponseTextDeltaEvent

    from unique_toolkit.app.unique_settings import UniqueSettings
    from unique_toolkit.content.schemas import ContentChunk


class ResponsesTextDeltaHandler:
    """Processes ``ResponseTextDeltaEvent``: applies replacers, accumulates text, emits SDK events.

    Private state: replacer chain, ``_full_text`` (normalized), ``_original_text`` (raw).
    """

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        replacers: list[StreamingReplacerProtocol],
        content_chunks: list[ContentChunk] | None = None,
        resolve_references: bool = False,
    ) -> None:
        self._settings = settings
        self._replacers = replacers
        self._content_chunks = content_chunks
        self._resolve_references = resolve_references
        self._full_text = ""
        self._original_text = ""

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> None:
        self._original_text += event.delta
        delta = event.delta
        for replacer in self._replacers:
            delta = replacer.process(delta)
        self._full_text += delta
        await self._emit_message_event()

    async def on_stream_end(self) -> None:
        remaining = ""
        for replacer in self._replacers:
            if remaining:
                remaining = replacer.process(remaining)
            remaining += replacer.flush()
        if remaining:
            self._full_text += remaining
            if self._settings.context.chat is not None:
                await self._emit_message_event()

        if self._resolve_references and self._settings.context.chat is not None:
            await self._persist_final_message()

    def get_text(self) -> tuple[str, str]:
        """Return ``(full_text, original_text)``."""
        return self._full_text, self._original_text

    def reset(self) -> None:
        self._full_text = ""
        self._original_text = ""
        for replacer in self._replacers:
            replacer.flush()

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
            ),
        )

    async def _persist_final_message(self) -> None:
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
