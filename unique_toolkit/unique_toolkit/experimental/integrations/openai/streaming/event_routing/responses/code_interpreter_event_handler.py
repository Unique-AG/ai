"""EventHandler for code interpreter call events — pure state accumulator.

The event handler consumes OpenAI Responses code-interpreter events and keeps a
per-``item_id`` ``(status, text)`` fingerprint to suppress duplicate
progress updates; each genuine transition is published as an
:class:`ActivityProgressUpdate` on the event-handler-owned
:class:`TypedEventBus` (:attr:`activity_bus`).

All SDK I/O (``MessageLog`` create/update, ``Message`` modify) lives in
subscribers reacting to the outer-bus :class:`ActivityProgress` event
(adapted by the orchestrator from :attr:`activity_bus`) and
:class:`MessagePersistingSubscriber` (which writes the streamed assistant
text — executed code is not duplicated into that message body).

Structurally this event handler owns a :class:`TypedEventBus` just like the
text event handlers do — the event routing package exposes that bus for the orchestrator
to subscribe to, so future progress-producing event handlers only need to
expose a ``activity_bus`` property to plug in.
"""

from __future__ import annotations

from openai.types.responses.response_code_interpreter_call_code_delta_event import (
    ResponseCodeInterpreterCallCodeDeltaEvent,
)
from openai.types.responses.response_code_interpreter_call_code_done_event import (
    ResponseCodeInterpreterCallCodeDoneEvent,
)
from openai.types.responses.response_code_interpreter_call_completed_event import (
    ResponseCodeInterpreterCallCompletedEvent,
)
from openai.types.responses.response_code_interpreter_call_in_progress_event import (
    ResponseCodeInterpreterCallInProgressEvent,
)
from openai.types.responses.response_code_interpreter_call_interpreting_event import (
    ResponseCodeInterpreterCallInterpretingEvent,
)

from unique_toolkit._common.event_bus import TypedEventBus
from unique_toolkit.experimental._internal.streaming import (
    ActivityProgressUpdate,
    ActivityStatus,
)

CodeInterpreterCallEvent = (
    ResponseCodeInterpreterCallCodeDoneEvent
    | ResponseCodeInterpreterCallCompletedEvent
    | ResponseCodeInterpreterCallCodeDeltaEvent
    | ResponseCodeInterpreterCallInProgressEvent
    | ResponseCodeInterpreterCallInterpretingEvent
)


class ResponsesCodeInterpreterEventHandler:
    """Accumulates code-interpreter state without performing any I/O.

    Publishes :class:`ActivityProgressUpdate` on its own
    :class:`TypedEventBus` (accessible via :attr:`activity_bus`) for
    every genuine state transition, deduplicated by a per-``item_id``
    ``(status, text)`` fingerprint.
    """

    def __init__(self) -> None:
        self._last_by_item: dict[str, tuple[ActivityStatus, str]] = {}
        self._activity_bus: TypedEventBus[ActivityProgressUpdate] = TypedEventBus()

    @property
    def activity_bus(self) -> TypedEventBus[ActivityProgressUpdate]:
        """Event-handler-local bus carrying progress updates as state transitions."""
        return self._activity_bus

    async def on_code_interpreter_event(self, event: CodeInterpreterCallEvent) -> None:
        """Map one OpenAI CI event to an optional progress update publish."""
        status: ActivityStatus
        if isinstance(event, ResponseCodeInterpreterCallCodeDoneEvent):
            text_update = "Code interpreter call completed"
            status = "COMPLETED"
        elif isinstance(event, ResponseCodeInterpreterCallCompletedEvent):
            text_update = "Code interpreter call completed"
            status = "COMPLETED"
        elif isinstance(event, ResponseCodeInterpreterCallCodeDeltaEvent):
            text_update = "Code interpreter call in progress"
            status = "RUNNING"
        elif isinstance(event, ResponseCodeInterpreterCallInProgressEvent):
            text_update = "Code interpreter call in progress"
            status = "RUNNING"
        else:  # ResponseCodeInterpreterCallInterpretingEvent
            text_update = "Code interpreter call interpreting"
            status = "RUNNING"

        item_id = event.item_id
        fingerprint = (status, text_update)
        if self._last_by_item.get(item_id) == fingerprint:
            return
        self._last_by_item[item_id] = fingerprint

        await self._activity_bus.publish_and_wait_async(
            ActivityProgressUpdate(
                correlation_id=item_id,
                status=status,
                text=text_update,
            )
        )

    async def on_stream_end(self) -> None:
        """No-op: progress transitions are published as they happen."""
        return

    def reset(self) -> None:
        """Clear accumulated state. Bus subscribers are preserved across requests."""
        self._last_by_item = {}
