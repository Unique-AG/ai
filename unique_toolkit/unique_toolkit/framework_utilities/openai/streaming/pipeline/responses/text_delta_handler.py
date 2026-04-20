"""Handler for ``ResponseTextDeltaEvent`` — accumulates text via replacers.

Pure state machine: applies streaming replacers and accumulates
``full_text`` and ``original_text``. Publishes a :class:`TextFlushed`
event on its own handler-owned :class:`TypedEventBus` at every flush
boundary so the orchestrator (or any other subscriber) can adapt it
into a :class:`TextDelta` without the handler knowing about bus-level
identifiers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from unique_toolkit._common.event_bus import TypedEventBus
from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)
from unique_toolkit.framework_utilities.openai.streaming.pipeline.protocols import (
    TextFlushed,
    TextState,
)

if TYPE_CHECKING:
    from openai.types.responses import ResponseTextDeltaEvent


class ResponsesTextDeltaHandler:
    """Accumulates text from ``ResponseTextDeltaEvent``.

    Responses streams are already pre-chunked by the provider — every
    non-empty delta is its own flush boundary and triggers a
    :class:`TextFlushed` publish. The bus is exposed via
    :attr:`flush_bus`; subscribers registered there survive handler
    resets (the orchestrator subscribes once at construction).
    """

    def __init__(
        self,
        *,
        replacers: list[StreamingReplacerProtocol],
    ) -> None:
        self._replacers = replacers
        self._state = TextState(full_text="", original_text="")
        self._flush_bus: TypedEventBus[TextFlushed] = TypedEventBus()

    @property
    def flush_bus(self) -> TypedEventBus[TextFlushed]:
        """Handler-local bus carrying :class:`TextFlushed` at every flush."""
        return self._flush_bus

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> None:
        """Process one delta; publish :class:`TextFlushed` on non-empty deltas."""
        if not event.delta:
            return

        self._state.original_text += event.delta

        delta = event.delta
        for replacer in self._replacers:
            delta = replacer.process(delta)
        self._state.full_text += delta

        await self._flush_bus.publish_and_wait_async(
            TextFlushed(
                full_text=self._state.full_text,
                original_text=self._state.original_text,
            )
        )

    async def on_stream_end(self) -> None:
        """Flush any replacer-buffered text and publish a final event if needed."""
        remaining = ""
        for replacer in self._replacers:
            if remaining:
                remaining = replacer.process(remaining)
            remaining += replacer.flush()

        if remaining:
            self._state.full_text += remaining
            await self._flush_bus.publish_and_wait_async(
                TextFlushed(
                    full_text=self._state.full_text,
                    original_text=self._state.original_text,
                )
            )

    def get_text(self) -> TextState:
        """Return accumulated normalised and original text."""
        return self._state

    def reset(self) -> None:
        """Clear accumulated state. Bus subscribers are preserved across requests."""
        self._state = TextState(full_text="", original_text="")
        for replacer in self._replacers:
            replacer.flush()
