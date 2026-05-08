"""Framework-agnostic streaming event handler types and lifecycle contract.

These types are **framework-agnostic** on purpose: they live in the
toolkit's domain-layer ``protocols`` package so alternative framework
adapters (future providers beyond OpenAI) can realize the same event handler
shape without pulling in OpenAI-specific imports. Concrete, OpenAI-typed
event handler protocols live next to their implementations under
``unique_toolkit.experimental.integrations.openai.streaming.event_routing.protocols``.

This module declares:

* The lifecycle contract every streaming event handler realizes
  (:class:`StreamEventHandlerProtocol`) plus the accumulated-text value
  (:class:`TextState`).
* Role-shaped base protocols that group members shared by every
  implementation of a role, regardless of the underlying API:
  :class:`StreamTextEventHandlerProtocol` for text accumulators and
  :class:`StreamToolCallEventHandlerProtocol` for tool-call accumulators.
  Framework-specific subprotocols only add the vendor-typed consumer
  methods (e.g. ``on_chunk`` / ``on_text_delta``).
* Event-handler bus payload dataclasses (:class:`TextFlushed`,
  :class:`ActivityProgressUpdate`) — carried on per-event handler
  :class:`TypedEventBus` instances, adapted by the orchestrator onto the
  outer :class:`StreamEventBus`.
* Structural capability protocols event routing aggregate across event handlers
  (:class:`AppendixProducer`, :class:`ActivityProducer`,
  :class:`UsageProducer`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from unique_toolkit._common.event_bus import TypedEventBus
    from unique_toolkit.language_model.schemas import (
        LanguageModelFunction,
        LanguageModelTokenUsage,
    )

ActivityStatus = Literal["RUNNING", "COMPLETED", "FAILED"]
"""Lifecycle state of a tool-like activity exposed to subscribers.

Framework-agnostic: the values describe observable progress (running,
finished, failed) without coupling to any vendor's event taxonomy. Lives
with :class:`ActivityProgressUpdate` because one is the type of the
other's ``status`` field.
"""


@dataclass
class TextState:
    """Accumulated assistant text: normalised (``full_text``) and raw model output (``original_text``)."""

    full_text: str
    original_text: str


class StreamEventHandlerProtocol(Protocol):
    """Lifecycle methods shared by every event handler (any OpenAI streaming surface).

    Event handlers that need to surface per-event signals (text flushes, tool
    activity progress, …) expose an event-handler-owned :class:`TypedEventBus`
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
    """The text event handler crossed a flush boundary.

    Carried on the event-handler-owned :class:`TypedEventBus` so subscribers
    (typically the orchestrator) can adapt it into a full :class:`TextUpdate`
    by attaching request context (``message_id`` / ``chat_id``). The
    payload mirrors the event handler's current :meth:`get_text` state at the
    moment of the flush.

    Flush boundaries combine two concerns: replacer hold-back release
    (e.g. a partial ``[source`` pattern finishing into ``[source1]``) and
    throttling (e.g. ``send_every_n_events`` on the Chat Completions
    event handler). The event handler stays ignorant of the outer bus and identity
    context — it only reports "now is a good time to publish".
    """

    full_text: str
    original_text: str
    chunk_index: int | None = None


@dataclass(frozen=True, slots=True)
class ActivityProgressUpdate:
    """Event-handler-local description of a single tool-activity progress transition.

    Carried on the event-handler-owned :class:`TypedEventBus` so the orchestrator
    can adapt it into an :class:`ActivityProgress` outer-bus event by
    attaching ``message_id`` / ``chat_id``. Event handlers that participate in
    tool-activity tracking publish one of these per genuine state change
    (deduplicated at the event handler level).
    """

    correlation_id: str
    status: ActivityStatus
    text: str
    order: int = 0


@runtime_checkable
class AppendixProducer(Protocol):
    """Optional capability: the event handler contributes to the final assistant message.

    When present, the event routing aggregates appendices across event handlers and
    attaches the tuple to :class:`StreamEnded`, so the message persister
    writes ``full_text + "".join(appendices)`` in a single round-trip. A
    return value of ``None`` means "nothing to append this run".
    """

    def get_appendix(self) -> str | None:
        """Return the text to append, or ``None`` if this run contributed nothing."""
        ...


@runtime_checkable
class ActivityProducer(Protocol):
    """Optional capability: the event handler reports tool-activity progress.

    Realizers expose an event-handler-owned :class:`TypedEventBus` publishing
    :class:`ActivityProgressUpdate` payloads on each genuine state
    transition (deduplicated at the event handler level). The orchestrator
    subscribes to this bus and adapts the updates onto the outer
    :class:`StreamEventBus` by attaching request context. Mirrors
    :class:`AppendixProducer` in spirit: both are named capabilities the
    event routing discovers on event handlers at wire-up time.
    """

    @property
    def activity_bus(self) -> TypedEventBus[ActivityProgressUpdate]:
        """Event-handler-owned bus publishing progress updates per state transition."""
        ...


@runtime_checkable
class UsageProducer(Protocol):
    """Optional capability: the event handler exposes token usage for a completed stream.

    Different streaming APIs surface usage in different places (for example,
    Responses has a completed event while other APIs may attach usage to a
    terminal chunk). This capability lets provider-specific event handlers expose
    the normalized toolkit usage shape without coupling the base lifecycle
    protocol to token accounting.
    """

    def get_usage(self) -> LanguageModelTokenUsage | None:
        """Return normalized token usage, or ``None`` when unavailable."""
        ...


class StreamTextEventHandlerProtocol(StreamEventHandlerProtocol, Protocol):
    """Base contract for any event handler that accumulates assistant text from a stream.

    Captures the role members shared by every text event handler regardless of
    the upstream API: an event-handler-owned :class:`TypedEventBus` publishing
    :class:`TextFlushed` at flush boundaries, plus :meth:`get_text` for
    inspecting the accumulated state. Framework-specific subprotocols
    add only the vendor-typed consumer method (e.g.
    ``on_chunk(ChatCompletionChunk)`` for Chat Completions,
    ``on_text_delta(ResponseTextDeltaEvent)`` for Responses).

    Pure state machine by design: no SDK, no outer bus, no knowledge of
    retrieved chunks — subscribers (typically the orchestrator) adapt
    :class:`TextFlushed` into full :class:`TextUpdate` events by attaching
    request context.
    """

    @property
    def text_bus(self) -> TypedEventBus[TextFlushed]:
        """Event-handler-owned bus publishing :class:`TextFlushed` at flush boundaries."""
        ...

    def get_text(self) -> TextState:
        """Return accumulated normalised and original text."""
        ...


class StreamToolCallEventHandlerProtocol(StreamEventHandlerProtocol, Protocol):
    """Base contract for any event handler that accumulates tool calls from a stream.

    Captures the role members shared by every tool-call event handler
    regardless of the upstream API: :meth:`get_tool_calls` returns the
    accumulated list of :class:`LanguageModelFunction`. Framework-specific
    subprotocols add only the vendor-typed consumer method(s) (e.g.
    ``on_chunk(ChatCompletionChunk)`` for Chat Completions, or the pair
    ``on_output_item_added`` / ``on_function_arguments_done`` for
    Responses).
    """

    def get_tool_calls(self) -> list[LanguageModelFunction]:
        """Return the list of tool calls observed so far, in arrival order."""
        ...
