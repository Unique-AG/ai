"""Domain events and the typed routing table published by streaming routers.

These decouple streaming *state machines* (handlers/routers) from
*side-effects* (message persistence, logging, analytics, ...). Handlers
accumulate state only; orchestrators (``*CompleteWithReferences``) publish
these events onto the per-event channels of :class:`StreamEventBus` so any
number of subscribers can react without touching router internals.

Design note: the bus deliberately exposes **one typed channel per concrete
event** instead of a ``TypedEventBus[StreamEvent]`` broadcasting a tagged
union. That keeps the publish/subscribe contract narrow, removes the
``isinstance`` re-dispatch that every subscriber used to carry, and makes
"only wire what the router can actually produce" fall out naturally — e.g.
:attr:`activity_progress` only gets a subscriber when a progress-producing
handler is present on the router.

The default wiring registers :class:`MessagePersistingSubscriber` (text
lifecycle) and, when the router exposes a progress producer,
:class:`ProgressLogPersister` (activity progress logs).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, Union

from unique_toolkit._common.event_bus import TypedEventBus
from unique_toolkit.protocols.streaming.common import ActivityStatus

if TYPE_CHECKING:
    from unique_toolkit.content.schemas import ContentChunk


@dataclass(frozen=True, slots=True)
class StreamStarted:
    """Published once before the stream loop begins.

    Attributes:
        message_id: Assistant message being streamed into.
        chat_id: Owning chat.
        content_chunks: Retrieved chunks available to subscribers for
            reference resolution. Intentionally carried on the event so
            text handlers never need to know about them.
    """

    message_id: str
    chat_id: str
    content_chunks: tuple[ContentChunk, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class TextDelta:
    """Published whenever the text handler crosses a flush boundary.

    Carries the currently-accumulated text (both normalised and raw) so
    subscribers can persist incremental updates without poking at handler
    internals.
    """

    message_id: str
    chat_id: str
    full_text: str
    original_text: str


@dataclass(frozen=True, slots=True)
class StreamEnded:
    """Published once after every handler has flushed and the stream is closed.

    Carries the final accumulated text for the authoritative persist, plus
    any ``appendices`` contributed by auxiliary handlers (e.g. a code
    interpreter block or tool-activity summary). Subscribers that write the
    assistant message are expected to concatenate ``appendices`` onto
    ``full_text`` in order, avoiding a second round-trip to the platform.
    """

    message_id: str
    chat_id: str
    full_text: str
    original_text: str
    appendices: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ActivityProgress:
    """Published when a tool-like activity changes its displayed progress state.

    Generic over the concrete activity (code interpreter, web search,
    retrieval, …): subscribers persist each update as a ``MessageLog``
    keyed by :attr:`correlation_id` so transitions for the same logical
    call are coalesced into a single log entry.

    Attributes:
        correlation_id: Stable idempotency key for the activity (e.g. the
            OpenAI ``item_id``). Subscribers use this to decide whether to
            create a new log entry or update an existing one.
        message_id: Assistant message the activity belongs to.
        chat_id: Owning chat.
        status: Current lifecycle state (``RUNNING`` / ``COMPLETED`` /
            ``FAILED``).
        text: Human-readable progress summary displayed to the user.
        order: Position hint when multiple activities are shown side by
            side; defaults to ``0``.
    """

    correlation_id: str
    message_id: str
    chat_id: str
    status: ActivityStatus
    text: str
    order: int = 0


StreamEvent = Union[StreamStarted, TextDelta, StreamEnded, ActivityProgress]
"""Documentation alias for the closed set of events published on a
:class:`StreamEventBus`. No code should subscribe to or publish this
union directly — pick the concrete channel on the bus instead."""


@dataclass(slots=True)
class StreamEventBus:
    """Routing table of typed pub/sub channels, one per concrete event.

    Each attribute is an independently-subscribable :class:`TypedEventBus`
    for a single event type. Orchestrators publish on the matching channel;
    subscribers subscribe only to the channels they care about — so
    ``isinstance`` re-dispatch at the subscriber boundary goes away, and
    wiring is naturally conditional (e.g. skip :attr:`activity_progress`
    entirely when the router has no progress-producing handler).

    Callers can attach extra subscribers after construction:

    .. code-block:: python

        orchestrator.bus.text_delta.subscribe(my_analytics_fn)
    """

    stream_started: TypedEventBus[StreamStarted] = field(default_factory=TypedEventBus)
    text_delta: TypedEventBus[TextDelta] = field(default_factory=TypedEventBus)
    stream_ended: TypedEventBus[StreamEnded] = field(default_factory=TypedEventBus)
    activity_progress: TypedEventBus[ActivityProgress] = field(
        default_factory=TypedEventBus
    )


class StreamSubscriber(Protocol):
    """Structural contract for anything that wants to react to stream events.

    A subscriber exposes a single :meth:`register` method that wires its
    per-event callbacks onto the relevant channels of the bus. This
    replaces passing a fan-out ``Handler[StreamEvent]`` callable: it keeps
    the subscriber in charge of deciding *which* channels it cares about,
    and avoids the orchestrator having to know each subscriber's event
    surface.
    """

    def register(self, bus: StreamEventBus) -> None:
        """Attach this subscriber's callbacks to the given bus."""
        ...


__all__ = [
    "ActivityProgress",
    "ActivityStatus",
    "StreamEnded",
    "StreamEvent",
    "StreamEventBus",
    "StreamStarted",
    "StreamSubscriber",
    "TextDelta",
]
