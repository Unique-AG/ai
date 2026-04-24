"""Handler for Chat Completion text deltas — accumulates text via replacers.

This handler is a *pure state machine*: it applies streaming replacers,
accumulates both ``full_text`` (normalised) and ``original_text`` (raw
model output), and tells its caller when a text boundary has been crossed.
It performs no SDK I/O and knows nothing about retrieved chunks; all
side-effects live in subscribers of :data:`StreamEvent`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.protocols import (
    TextState,
)

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk


class ChatCompletionTextHandler:
    """Accumulates text from ``ChatCompletionChunk`` events.

    Private state: replacer chain, :class:`TextState` (normalised + raw),
    and a flush counter that throttles observable boundaries.
    """

    def __init__(
        self,
        *,
        replacers: list[StreamingReplacerProtocol],
        send_every_n_events: int = 1,
    ) -> None:
        self._replacers = replacers
        self._send_every_n_events = max(1, send_every_n_events)
        self._state = TextState(full_text="", original_text="")

    async def on_chunk(self, event: ChatCompletionChunk, *, index: int) -> bool:
        """Process one chunk.

        Returns:
            True if this chunk crosses a flush boundary (``send_every_n_events``)
            and carried content, signalling the caller it should observe the
            updated :class:`TextState`. False otherwise.
        """
        if len(event.choices) == 0:
            return False

        content = event.choices[0].delta.content or ""
        if not content:
            return False

        self._state.original_text += content

        delta = content
        for replacer in self._replacers:
            delta = replacer.process(delta)
        self._state.full_text += delta

        return (index + 1) % self._send_every_n_events == 0

    async def on_stream_end(self) -> bool:
        """Flush any replacer-buffered text.

        Returns:
            True if flushing produced observable text that the caller should
            surface before publishing the final ``StreamEnded`` event.
        """
        remaining = ""
        for replacer in self._replacers:
            if remaining:
                remaining = replacer.process(remaining)
            remaining += replacer.flush()

        if remaining:
            self._state.full_text += remaining
            return True
        return False

    def get_text(self) -> TextState:
        """Return accumulated normalised and original text."""
        return self._state

    def reset(self) -> None:
        self._state = TextState(full_text="", original_text="")
        for replacer in self._replacers:
            replacer.flush()
