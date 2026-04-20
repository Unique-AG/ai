"""Shared streaming handler types and the base lifecycle protocol.

API-specific handler protocols live in :mod:`chat_completions` and :mod:`responses`.
This module also declares:

* Handler-bus payload dataclasses (:class:`TextFlushed`,
  :class:`ActivityProgressUpdate`) — carried on per-handler
  :class:`TypedEventBus` instances, adapted by the orchestrator onto the
  outer :class:`StreamEventBus`.
* Structural protocols for optional capabilities the pipeline aggregates
  across handlers (currently :class:`AppendixProducer`).
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

    Handlers that need to surface per-event signals (text flushes, tool
    activity progress, …) expose a handler-owned :class:`TypedEventBus`
    instead of returning a signal from their lifecycle methods — see
    :class:`TextFlushed` / :class:`ActivityProgressUpdate` for payloads.
    """

    async def on_stream_end(self) -> None:
        """Finalize after the stream is exhausted (flush buffers, release resources)."""
        ...

    def reset(self) -> None:
        """Clear all per-run state for reuse."""
        ...


@dataclass(frozen=True, slots=True)
class TextFlushed:
    """The text handler crossed a flush boundary.

    Carried on the handler-owned :class:`TypedEventBus` so subscribers
    (typically the orchestrator) can adapt it into a full :class:`TextDelta`
    by attaching request context (``message_id`` / ``chat_id``). The
    payload mirrors the handler's current :meth:`get_text` state at the
    moment of the flush.

    Flush boundaries combine two concerns: replacer hold-back release
    (e.g. a partial ``[source`` pattern finishing into ``[source1]``) and
    throttling (e.g. ``send_every_n_events`` on the Chat Completions
    handler). The handler stays ignorant of the outer bus and identity
    context — it only reports "now is a good time to publish".
    """

    full_text: str
    original_text: str
    chunk_index: int | None = None


@dataclass(frozen=True, slots=True)
class ActivityProgressUpdate:
    """Handler-local description of a single tool-activity progress transition.

    Carried on the handler-owned :class:`TypedEventBus` so the orchestrator
    can adapt it into an :class:`ActivityProgress` outer-bus event by
    attaching ``message_id`` / ``chat_id``. Handlers that participate in
    tool-activity tracking publish one of these per genuine state change
    (deduplicated at the handler level).
    """

    correlation_id: str
    status: ActivityStatus
    text: str
    order: int = 0


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
