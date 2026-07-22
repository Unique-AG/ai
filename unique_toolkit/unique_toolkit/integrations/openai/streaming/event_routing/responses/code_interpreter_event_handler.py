"""EventHandler for code interpreter call events — pure state accumulator.

The event handler consumes OpenAI Responses code-interpreter lifecycle events
(``in_progress`` / ``interpreting`` / ``completed``; ``delta`` and ``code.done``
carry no displayed progress and are ignored) and keeps a per-``correlation_id``
``(status, text)`` fingerprint to suppress duplicate progress updates; each
genuine transition is published as an :class:`ActivityProgressUpdate` on the
event-handler-owned :class:`TypedEventBus` (:attr:`activity_bus`).

Each call surfaces as two correlation ids, mirroring the orchestrator's normal
tool-call display: a one-shot "Triggered Tool Calls" summary published under
``{item_id}-triggered`` on the ``in_progress`` event, and the "Code Execution"
detail published under ``item_id`` on every lifecycle transition.

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
from unique_toolkit._internal.streaming import (
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
    every genuine state transition, deduplicated by a per-``correlation_id``
    ``(status, text)`` fingerprint. Lifecycle events (``in_progress`` /
    ``interpreting`` / ``completed``) drive the ``item_id`` detail update;
    the ``in_progress`` event additionally emits a one-shot "Triggered Tool
    Calls" summary under ``{item_id}-triggered``. ``delta`` and ``code.done``
    events are ignored.
    """

    def __init__(self) -> None:
        self._last_by_item: dict[str, tuple[ActivityStatus, str]] = {}
        self._activity_bus: TypedEventBus[ActivityProgressUpdate] = TypedEventBus()

    @property
    def activity_bus(self) -> TypedEventBus[ActivityProgressUpdate]:
        """Event-handler-local bus carrying progress updates as state transitions."""
        return self._activity_bus

    async def on_code_interpreter_event(self, event: CodeInterpreterCallEvent) -> None:
        """Map one OpenAI CI event to its progress update publishes."""
        progress = self._progress_for_event(event)
        if progress is None:
            return
        status, text_update = progress

        if event.type == "response.code_interpreter_call.in_progress":
            await self._publish_if_changed(
                f"{event.item_id}-triggered",
                "COMPLETED",
                "**Triggered Tool Calls:**\n - Code Execution",
            )
        await self._publish_if_changed(event.item_id, status, text_update)

    @staticmethod
    def _build_code_execution_message(message: str) -> str:
        return f"**Code Execution**\n {message}".strip()

    def _progress_for_event(
        self, event: CodeInterpreterCallEvent
    ) -> tuple[ActivityStatus, str] | None:
        """Decode a CI event into its ``(status, text)``, or ``None`` to ignore it."""
        if event.type == "response.code_interpreter_call.completed":
            return "COMPLETED", self._build_code_execution_message("")
        if event.type == "response.code_interpreter_call.in_progress":
            return "RUNNING", self._build_code_execution_message("Writing Code")
        if event.type == "response.code_interpreter_call.interpreting":
            return "RUNNING", self._build_code_execution_message("Executing Code")
        return None

    async def _publish_if_changed(
        self, correlation_id: str, status: ActivityStatus, text: str
    ) -> None:
        """Publish a progress update unless its ``(status, text)`` is unchanged."""
        fingerprint = (status, text)
        if self._last_by_item.get(correlation_id) == fingerprint:
            return
        self._last_by_item[correlation_id] = fingerprint
        await self._activity_bus.publish_and_wait_async(
            ActivityProgressUpdate(
                correlation_id=correlation_id,
                status=status,
                text=text,
            )
        )

    async def on_stream_end(self) -> None:
        """No-op: progress transitions are published as they happen."""
        return

    def reset(self) -> None:
        """Clear accumulated state. Bus subscribers are preserved across requests."""
        self._last_by_item = {}
