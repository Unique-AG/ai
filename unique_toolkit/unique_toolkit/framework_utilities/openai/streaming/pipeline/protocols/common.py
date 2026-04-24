"""Shared streaming handler types and the base lifecycle protocol.

API-specific handler protocols live in :mod:`chat_completions` and :mod:`responses`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class TextState:
    """Accumulated assistant text: normalised (``full_text``) and raw model output (``original_text``)."""

    full_text: str
    original_text: str


class StreamHandlerProtocol(Protocol):
    """Lifecycle methods shared by every event handler (any OpenAI streaming surface).

    Text handlers narrow :meth:`on_stream_end` to return ``bool`` so callers
    can observe a residual flush; all other handlers return ``None``.
    """

    async def on_stream_end(self) -> None:
        """Finalize after the stream is exhausted (flush buffers, release resources)."""
        ...

    def reset(self) -> None:
        """Clear all per-run state for reuse."""
        ...
