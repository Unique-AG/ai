"""Handler for Chat Completion text deltas — accumulates text, applies replacers, emits SDK events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import unique_sdk

from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.protocols import (
    TextState,
)

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

    from unique_toolkit.app.unique_settings import UniqueSettings


class ChatCompletionTextHandler:
    """Processes text content from ``ChatCompletionChunk``: applies replacers,
    accumulates both original and normalized text, emits SDK events.

    Private state: replacer chain and ``TextState`` (normalised vs raw).
    """

    def __init__(
        self,
        settings: UniqueSettings,
        *,
        replacers: list[StreamingReplacerProtocol],
        send_every_n_events: int = 1,
    ) -> None:
        self._settings = settings
        self._replacers = replacers
        self._send_every_n_events = max(1, send_every_n_events)
        self._state = TextState(full_text="", original_text="")

    async def on_chunk(self, event: ChatCompletionChunk, *, index: int) -> None:
        if len(event.choices) == 0 or self._settings.context.chat is None:
            return

        content = event.choices[0].delta.content or ""
        self._state.original_text += content

        delta = content
        for replacer in self._replacers:
            delta = replacer.process(delta)
        self._state.full_text += delta

        if (index + 1) % self._send_every_n_events == 0:
            await self._emit_message_event()

    async def on_stream_end(self) -> None:
        remaining = ""
        for replacer in self._replacers:
            if remaining:
                remaining = replacer.process(remaining)
            remaining += replacer.flush()
        if remaining:
            self._state.full_text += remaining
            await self._emit_message_event()

        if self._settings.context.chat is not None:
            await self._persist_final_message()

    def get_text(self) -> TextState:
        """Return accumulated normalised and original text."""
        return self._state

    def reset(self) -> None:
        self._state = TextState(full_text="", original_text="")
        for replacer in self._replacers:
            replacer.flush()

    async def _emit_message_event(self) -> None:
        chat = self._settings.context.chat
        assert chat is not None

        # await unique_sdk.Message.create_event_async(
        #    user_id=self._settings.context.auth.user_id.get_secret_value(),
        #    company_id=self._settings.context.auth.company_id.get_secret_value(),
        #    **unique_sdk.Message.CreateEventParams(
        #        chatId=chat.chat_id,
        #        messageId=chat.last_assistant_message_id,
        #        text=self._state.full_text,
        #        originalText=self._state.original_text,
        #    ),
        # )

        # Using modify as it renders the references correctly while create event does not
        await unique_sdk.Message.modify_async(
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            id=chat.last_assistant_message_id,
            chatId=chat.chat_id,
            text=self._state.full_text or None,
            originalText=self._state.original_text,
        )

    async def _persist_final_message(self) -> None:
        chat = self._settings.context.chat
        assert chat is not None
        await unique_sdk.Message.modify_async(
            user_id=self._settings.context.auth.user_id.get_secret_value(),
            company_id=self._settings.context.auth.company_id.get_secret_value(),
            id=chat.last_assistant_message_id,
            chatId=chat.chat_id,
            text=self._state.full_text or None,
            originalText=self._state.original_text or None,
            stoppedStreamingAt=datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),  # type: ignore
        )
