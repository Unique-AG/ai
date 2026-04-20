"""Domain events published by streaming pipelines.

These decouple streaming *state machines* (handlers/pipelines) from
*side-effects* (message persistence, logging, analytics, ...). Handlers
accumulate state only; orchestrators (``*CompleteWithReferences``) publish
these events onto a :class:`TypedEventBus[StreamEvent]` so any number of
subscribers can react without touching pipeline internals.

The default wiring registers :class:`MessagePersistingSubscriber`, which
owns ``unique_sdk.Message.modify_async`` calls and reference filtering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Union

from unique_toolkit._common.event_bus import TypedEventBus

if TYPE_CHECKING:
    from unique_toolkit.content.schemas import ContentChunk


ActivityStatus = Literal["RUNNING", "COMPLETED", "FAILED"]


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
"""Tagged union of every event a streaming pipeline can publish."""


StreamEventBus = TypedEventBus[StreamEvent]
"""Typed :class:`TypedEventBus` specialised for :data:`StreamEvent`."""


__all__ = [
    "ActivityProgress",
    "ActivityStatus",
    "StreamEnded",
    "StreamEvent",
    "StreamEventBus",
    "StreamStarted",
    "TextDelta",
]
