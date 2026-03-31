"""Handler for ``ResponseTextDeltaEvent`` — accumulates text, applies replacers, emits SDK events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import unique_sdk

from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)

if TYPE_CHECKING:
    from openai.types.responses import ResponseTextDeltaEvent

    from unique_toolkit.app.unique_settings import UniqueSettings


class ResponsesTextDeltaHandler:
    """Processes ``ResponseTextDeltaEvent``: applies replacers, accumulates text, emits SDK events.

    Private state: replacer chain, ``_full_text`` (normalized), ``_original_text`` (raw).
    """

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        replacers: list[StreamingReplacerProtocol],
    ) -> None:
        self._settings = settings
        self._replacers = replacers
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

        if self._settings.context.chat is not None:
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

        # Using modify as it renders the references correctly while create event does not
        await unique_sdk.Message.modify_async(
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            id=chat.last_assistant_message_id,
            chatId=chat.chat_id,
            text=self._full_text or None,
            originalText=self._original_text or None,
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
            originalText=self._original_text or None,
            stoppedStreamingAt=datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),  # type: ignore
        )
