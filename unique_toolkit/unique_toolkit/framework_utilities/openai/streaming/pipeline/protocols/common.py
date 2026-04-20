"""Shared streaming handler types and the base lifecycle protocol.

API-specific handler protocols live in :mod:`chat_completions` and :mod:`responses`.
This module also declares small *mix-in* structural protocols for optional
capabilities (activity progress, final-message appendices) so the pipeline
can collect contributions from any conforming handler without hard-coding
per-slot knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..events import ActivityStatus


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


@dataclass(frozen=True, slots=True)
class ActivityProgressUpdate:
    """Handler-local description of a single tool-activity progress transition.

    Handlers that participate in tool-activity tracking accumulate these
    and expose them via :meth:`ActivityProgressProducer.drain_pending`. The
    orchestrator wraps each update into an :class:`ActivityProgress` bus
    event by attaching ``message_id`` / ``chat_id``, so handlers stay
    ignorant of bus-level identifiers.
    """

    correlation_id: str
    status: ActivityStatus
    text: str
    order: int = 0


@runtime_checkable
class ActivityProgressProducer(Protocol):
    """Optional capability: the handler emits per-item progress updates.

    Any handler exposing this shape contributes to the pipeline's
    :meth:`drain_activity_progress` without needing a dedicated pipeline
    slot. The pipeline iterates its handlers and probes for this protocol
    at runtime via :func:`isinstance`, so adding a new progress-producing
    handler (e.g. a web-search progress handler) requires no pipeline
    edits.
    """

    def drain_pending(self) -> list[ActivityProgressUpdate]:
        """Return and clear progress updates observed since the previous call."""
        ...


@runtime_checkable
class AppendixProducer(Protocol):
    """Optional capability: the handler contributes to the final assistant message.

    When present, the pipeline aggregates appendices across handlers and
    attaches the tuple to :class:`StreamEnded`, so the message persister
    writes ``full_text + "".join(appendices)`` in a single round-trip. A
    return value of ``None`` means "nothing to append this run".
    """

    def get_appendix(self) -> str | None:
        """Return the text to append, or ``None`` if this run contributed nothing."""
        ...
