"""Handler for code interpreter call events — pure state accumulator.

The handler consumes OpenAI Responses code-interpreter events and keeps two
pieces of derived state:

* A per-``item_id`` (status, text) fingerprint used to suppress duplicate
  progress updates; each genuine transition is published as an
  :class:`ActivityProgressUpdate` on the handler-owned
  :class:`TypedEventBus` (:attr:`activity_bus`).
* The concatenated code the model executed, exposed as an assistant-message
  appendix via :meth:`get_appendix` for the orchestrator to attach to the
  final :class:`StreamEnded` event.

All SDK I/O (``MessageLog`` create/update, ``Message`` modify) lives in
subscribers reacting to the outer-bus :class:`ActivityProgress` event
(adapted by the orchestrator from :attr:`activity_bus`) and the
appendix-aware :class:`MessagePersistingSubscriber`.

Structurally this handler owns a :class:`TypedEventBus` just like the
text handlers do — the pipeline exposes that bus for the orchestrator
to subscribe to, so future progress-producing handlers only need to
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
from unique_toolkit.protocols.streaming import ActivityProgressUpdate, ActivityStatus

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

    Publishes :class:`ActivityProgressUpdate` on its own
    :class:`TypedEventBus` (accessible via :attr:`activity_bus`) for
    every genuine state transition, deduplicated by a per-``item_id``
    ``(status, text)`` fingerprint. Exposes the executed-code appendix
    via :meth:`get_appendix` for the orchestrator to attach to
    :class:`StreamEnded`.
    """

    def __init__(self) -> None:
        self._code: str = ""
        self._last_by_item: dict[str, tuple[ActivityStatus, str]] = {}
        self._activity_bus: TypedEventBus[ActivityProgressUpdate] = TypedEventBus()

    @property
    def activity_bus(self) -> TypedEventBus[ActivityProgressUpdate]:
        """Handler-local bus carrying progress updates as state transitions."""
        return self._activity_bus

    async def on_code_interpreter_event(self, event: CodeInterpreterCallEvent) -> None:
        """Map one OpenAI CI event to an optional progress update publish.

        Code accumulation intentionally uses the *done-only* strategy: the
        terminating :class:`ResponseCodeInterpreterCallCodeDoneEvent` carries
        the fully-assembled ``code`` string, and we snapshot it there rather
        than accumulating deltas. The previous dual strategy
        (``_code += delta`` alongside ``_code = event.code``) silently
        relied on the undocumented provider ordering "done comes after all
        deltas with the full code" — when those assumptions drifted it was
        easy to end up with duplicated or truncated appendices. Deltas now
        only drive the progress-update publish.
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

        await self._activity_bus.publish_and_wait_async(
            ActivityProgressUpdate(
                correlation_id=item_id,
                status=status,
                text=text_update,
            )
        )

    def get_appendix(self) -> str | None:
        """Return the formatted code appendix, or ``None`` if no code ran."""
        if not self._code:
            return None
        return _APPENDIX_PREAMBLE + self._code + _APPENDIX_SUFFIX

    async def on_stream_end(self) -> None:
        """No-op: progress transitions are published as they happen."""
        return

    def reset(self) -> None:
        """Clear accumulated state. Bus subscribers are preserved across requests."""
        self._code = ""
        self._last_by_item = {}
