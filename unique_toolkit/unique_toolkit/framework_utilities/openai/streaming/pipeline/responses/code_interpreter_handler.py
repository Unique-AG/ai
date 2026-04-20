"""Handler for code interpreter call events — pure state accumulator.

The handler consumes OpenAI Responses code-interpreter events and keeps two
pieces of derived state:

* A per-``item_id`` (status, text) fingerprint used to suppress duplicate
  progress updates; each genuine transition becomes an
  :class:`ActivityProgressUpdate` in the pending queue (the generic
  handler-bridge shape defined in :mod:`protocols.common`).
* The concatenated code the model executed, exposed as an assistant-message
  appendix via :meth:`get_appendix` for the orchestrator to attach to the
  final :class:`StreamEnded` event.

All SDK I/O (``MessageLog`` create/update, ``Message`` modify) lives in
subscribers reacting to :class:`ActivityProgress` and the appendix-aware
:class:`MessagePersistingSubscriber`.

Structurally, this handler is one of possibly many
:class:`ActivityProgressProducer` + :class:`AppendixProducer` implementations
— the pipeline discovers contributors via ``isinstance`` checks rather than
a CI-specific slot, so future progress-producing handlers need zero
pipeline changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

from ..protocols.common import ActivityProgressUpdate

if TYPE_CHECKING:
    from ..events import ActivityStatus

CodeInterpreterCallEvent = (
    ResponseCodeInterpreterCallCodeDoneEvent
    | ResponseCodeInterpreterCallCompletedEvent
    | ResponseCodeInterpreterCallCodeDeltaEvent
    | ResponseCodeInterpreterCallInProgressEvent
    | ResponseCodeInterpreterCallInterpretingEvent
)

_APPENDIX_PREAMBLE = "\n used the following code to generate the response: ```\n"
_APPENDIX_SUFFIX = "\n```"


class ResponsesCodeInterpreterHandler:
    """Accumulates code-interpreter state without performing any I/O.

    Implements the :class:`ActivityProgressProducer` and
    :class:`AppendixProducer` capability protocols structurally — the
    pipeline picks it up via ``isinstance`` alongside any other handler
    exposing the same shape.

    Private state: ``_code`` (accumulated executed code), ``_last_by_item``
    (per ``item_id`` fingerprint used to skip duplicate updates), and
    ``_pending`` (updates waiting to be drained by the orchestrator).
    """

    def __init__(self) -> None:
        self._code: str = ""
        self._last_by_item: dict[str, tuple[ActivityStatus, str]] = {}
        self._pending: list[ActivityProgressUpdate] = []

    async def on_code_interpreter_event(self, event: CodeInterpreterCallEvent) -> None:
        """Map one OpenAI CI event to an optional progress update.

        Pure: mutates only handler state and enqueues a pending update when
        the (status, text) pair for ``item_id`` changes.
        """
        status: ActivityStatus
        if isinstance(event, ResponseCodeInterpreterCallCodeDoneEvent):
            self._code = event.code
            text_update = "Code interpreter call completed"
            status = "COMPLETED"
        elif isinstance(event, ResponseCodeInterpreterCallCompletedEvent):
            text_update = "Code interpreter call completed"
            status = "COMPLETED"
        elif isinstance(event, ResponseCodeInterpreterCallCodeDeltaEvent):
            self._code += event.delta
            text_update = "Code interpreter call in progress"
            status = "RUNNING"
        elif isinstance(event, ResponseCodeInterpreterCallInProgressEvent):
            text_update = "Code interpreter call in progress"
            status = "RUNNING"
        elif isinstance(event, ResponseCodeInterpreterCallInterpretingEvent):
            text_update = "Code interpreter call interpreting"
            status = "RUNNING"
        else:
            return

        item_id = event.item_id
        fingerprint = (status, text_update)
        if self._last_by_item.get(item_id) == fingerprint:
            return
        self._last_by_item[item_id] = fingerprint
        self._pending.append(
            ActivityProgressUpdate(
                correlation_id=item_id,
                status=status,
                text=text_update,
            )
        )

    def drain_pending(self) -> list[ActivityProgressUpdate]:
        """Return and clear all pending progress updates.

        The orchestrator calls this after dispatching each stream event and
        publishes the results onto the bus.
        """
        drained = self._pending
        self._pending = []
        return drained

    def get_appendix(self) -> str | None:
        """Return the formatted code appendix, or ``None`` if no code ran.

        The orchestrator attaches this string to :class:`StreamEnded` so
        the message persister can write ``full_text + appendix`` in a
        single round-trip.
        """
        if not self._code:
            return None
        return _APPENDIX_PREAMBLE + self._code + _APPENDIX_SUFFIX

    async def on_stream_end(self) -> None:
        """No-op: the handler has no resources to release."""
        return

    def reset(self) -> None:
        self._code = ""
        self._last_by_item = {}
        self._pending = []
