"""Handler for Chat Completion text deltas — accumulates text via replacers.

This handler is a *pure state machine*: it applies streaming replacers and
accumulates both ``full_text`` (normalised) and ``original_text`` (raw
model output). At every flush boundary it publishes a :class:`TextFlushed`
event on its own handler-owned :class:`TypedEventBus` so external
subscribers (typically the orchestrator, optionally tests or tracers) can
react without the handler needing to know about the outer
:class:`StreamEventBus`, ``message_id``, or ``chat_id``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from unique_toolkit._common.event_bus import TypedEventBus
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)
from unique_toolkit.protocols.streaming import TextFlushed, TextState

if TYPE_CHECKING:
    from openai.types.chat.chat_completion_chunk import ChatCompletionChunk


class ChatCompletionTextHandler:
    """Accumulates text from ``ChatCompletionChunk`` events.

    Private state: replacer chain, :class:`TextState` (normalised + raw),
    a flush counter that throttles observable boundaries, and a
    :class:`TypedEventBus` carrying :class:`TextFlushed` events. Expose
    the bus via :attr:`text_bus` so the orchestrator can subscribe once
    at construction and adapt each flush into a :class:`TextDelta`.
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
        # Counts content-bearing chunks only — role-only / tool-call-only
        # chunks must not shift the flush boundary, otherwise callers that
        # set ``send_every_n_events`` to throttle SDK writes see irregular
        # (or missing) flushes.
        self._content_chunk_index = 0
        self._text_bus: TypedEventBus[TextFlushed] = TypedEventBus()

    @property
    def text_bus(self) -> TypedEventBus[TextFlushed]:
        """Handler-local bus carrying :class:`TextFlushed` at every flush."""
        return self._text_bus

    async def on_chunk(self, event: ChatCompletionChunk) -> None:
        """Process one chunk; publish :class:`TextFlushed` on flush boundaries.

        A flush is emitted only when the chunk carries content *and* crosses
        the configured ``send_every_n_events`` boundary — matching the prior
        bool-return semantics. All other chunks silently accumulate state.
        """
        if len(event.choices) == 0:
            return

        content = event.choices[0].delta.content or ""
        if not content:
            return

        # Increment only after the content guards so the flush boundary
        # tracks content-bearing chunks — see ``_content_chunk_index``.
        index = self._content_chunk_index
        self._content_chunk_index += 1

        self._state.original_text += content

        delta = content
        for replacer in self._replacers:
            delta = replacer.process(delta)
        self._state.full_text += delta

        if (index + 1) % self._send_every_n_events == 0:
            await self._text_bus.publish_and_wait_async(
                TextFlushed(
                    full_text=self._state.full_text,
                    original_text=self._state.original_text,
                    chunk_index=index,
                )
            )

    async def on_stream_end(self) -> None:
        """Flush any replacer-buffered text and publish a final :class:`TextFlushed`.

        Subscribers can rely on a trailing event when residual replacer
        output becomes observable at stream end — matching the prior
        bool-return semantics ("residual flush produced text").
        """
        remaining = ""
        for replacer in self._replacers:
            if remaining:
                remaining = replacer.process(remaining)
            remaining += replacer.flush()

        if remaining:
            self._state.full_text += remaining
            await self._text_bus.publish_and_wait_async(
                TextFlushed(
                    full_text=self._state.full_text,
                    original_text=self._state.original_text,
                )
            )

    def get_text(self) -> TextState:
        """Return accumulated normalised and original text."""
        return self._state

    def reset(self) -> None:
        """Clear accumulated state. Bus subscribers are intentionally preserved
        across requests — the orchestrator subscribes once at construction."""
        self._state = TextState(full_text="", original_text="")
        self._content_chunk_index = 0
        for replacer in self._replacers:
            replacer.flush()
