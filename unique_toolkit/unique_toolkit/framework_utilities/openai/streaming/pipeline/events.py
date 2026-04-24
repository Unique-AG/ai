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
from typing import TYPE_CHECKING, Union

from unique_toolkit._common.event_bus import TypedEventBus

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

    Carries the final accumulated text for the authoritative persist.
    """

    message_id: str
    chat_id: str
    full_text: str
    original_text: str


StreamEvent = Union[StreamStarted, TextDelta, StreamEnded]
"""Tagged union of every event a streaming pipeline can publish."""


StreamEventBus = TypedEventBus[StreamEvent]
"""Typed :class:`TypedEventBus` specialised for :data:`StreamEvent`."""


__all__ = [
    "StreamEnded",
    "StreamEvent",
    "StreamEventBus",
    "StreamStarted",
    "TextDelta",
]
