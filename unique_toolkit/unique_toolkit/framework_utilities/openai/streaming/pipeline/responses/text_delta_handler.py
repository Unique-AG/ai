"""Handler for ``ResponseTextDeltaEvent`` — accumulates text via replacers.

Pure state machine: applies streaming replacers, accumulates ``full_text``
and ``original_text``, signals to its caller whether a text boundary was
crossed. Performs no SDK I/O and has no knowledge of retrieved chunks —
side-effects live in :data:`StreamEvent` subscribers.
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
    from openai.types.responses import ResponseTextDeltaEvent


class ResponsesTextDeltaHandler:
    """Accumulates text from ``ResponseTextDeltaEvent``.

    Private state: replacer chain and :class:`TextState` (normalised + raw).
    Every non-empty delta crosses a flush boundary (Responses streams are
    already pre-chunked by the provider).
    """

    def __init__(
        self,
        *,
        replacers: list[StreamingReplacerProtocol],
    ) -> None:
        self._replacers = replacers
        self._state = TextState(full_text="", original_text="")

    async def on_text_delta(self, event: ResponseTextDeltaEvent) -> bool:
        """Process one delta.

        Returns:
            True if the delta produced observable text; False if the delta
            was empty.
        """
        if not event.delta:
            return False

        self._state.original_text += event.delta

        delta = event.delta
        for replacer in self._replacers:
            delta = replacer.process(delta)
        self._state.full_text += delta
        return True

    async def on_stream_end(self) -> bool:
        """Flush any replacer-buffered text.

        Returns:
            True if flushing produced observable text.
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
