"""Framework-agnostic streaming handler types and lifecycle contract.

These types are **framework-agnostic** on purpose: they live in the
toolkit's domain-layer ``protocols`` package so alternative framework
adapters (future providers beyond OpenAI) can realize the same handler
shape without pulling in OpenAI-specific imports. Concrete, OpenAI-typed
handler protocols live next to their implementations under
``unique_toolkit.framework_utilities.openai.streaming.pipeline.protocols``.

This module declares:

* The lifecycle contract every streaming handler realizes
  (:class:`StreamHandlerProtocol`) plus the accumulated-text value
  (:class:`TextState`).
* Role-shaped base protocols that group members shared by every
  implementation of a role, regardless of the underlying API:
  :class:`StreamTextHandlerProtocol` for text accumulators and
  :class:`StreamToolCallHandlerProtocol` for tool-call accumulators.
  Framework-specific subprotocols only add the vendor-typed consumer
  methods (e.g. ``on_chunk`` / ``on_text_delta``).
* Handler-bus payload dataclasses (:class:`TextFlushed`,
  :class:`ActivityProgressUpdate`) — carried on per-handler
  :class:`TypedEventBus` instances, adapted by the orchestrator onto the
  outer :class:`StreamEventBus`.
* Structural capability protocols pipelines aggregate across handlers
  (:class:`AppendixProducer`, :class:`ActivityProducer`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from unique_toolkit._common.event_bus import TypedEventBus
    from unique_toolkit.language_model.schemas import LanguageModelFunction

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


@runtime_checkable
class ActivityProducer(Protocol):
    """Optional capability: the handler reports tool-activity progress.

    Realizers expose a handler-owned :class:`TypedEventBus` publishing
    :class:`ActivityProgressUpdate` payloads on each genuine state
    transition (deduplicated at the handler level). The orchestrator
    subscribes to this bus and adapts the updates onto the outer
    :class:`StreamEventBus` by attaching request context. Mirrors
    :class:`AppendixProducer` in spirit: both are named capabilities the
    pipeline discovers on handlers at wire-up time.
    """

    @property
    def activity_bus(self) -> TypedEventBus[ActivityProgressUpdate]:
        """Handler-owned bus publishing progress updates per state transition."""
        ...


class StreamTextHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Base contract for any handler that accumulates assistant text from a stream.

    Captures the role members shared by every text handler regardless of
    the upstream API: a handler-owned :class:`TypedEventBus` publishing
    :class:`TextFlushed` at flush boundaries, plus :meth:`get_text` for
    inspecting the accumulated state. Framework-specific subprotocols
    add only the vendor-typed consumer method (e.g.
    ``on_chunk(ChatCompletionChunk)`` for Chat Completions,
    ``on_text_delta(ResponseTextDeltaEvent)`` for Responses).

    Pure state machine by design: no SDK, no outer bus, no knowledge of
    retrieved chunks — subscribers (typically the orchestrator) adapt
    :class:`TextFlushed` into full :class:`TextDelta` events by attaching
    request context.
    """

    @property
    def text_bus(self) -> TypedEventBus[TextFlushed]:
        """Handler-owned bus publishing :class:`TextFlushed` at flush boundaries."""
        ...

    def get_text(self) -> TextState:
        """Return accumulated normalised and original text."""
        ...


class StreamToolCallHandlerProtocol(StreamHandlerProtocol, Protocol):
    """Base contract for any handler that accumulates tool calls from a stream.

    Captures the role members shared by every tool-call handler
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
