"""Tests for ``ResponsesCodeInterpreterEventHandler`` — progress-update dedup."""

from __future__ import annotations

import pytest
from openai.types.responses.response_code_interpreter_call_code_delta_event import (
    ResponseCodeInterpreterCallCodeDeltaEvent,
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

from unique_toolkit.experimental._internal.streaming import (
    ActivityProgressUpdate,
    AppendixProducer,
)
from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.code_interpreter_event_handler import (
    ResponsesCodeInterpreterEventHandler,
)

_TRIGGERED_TEXT = "**Triggered Tool Calls:**\n - Code Execution"


def _delta(item_id: str, text: str) -> ResponseCodeInterpreterCallCodeDeltaEvent:
    return ResponseCodeInterpreterCallCodeDeltaEvent.model_construct(
        type="response.code_interpreter_call_code.delta",
        item_id=item_id,
        output_index=0,
        delta=text,
        sequence_number=0,
    )


def _in_progress(item_id: str) -> ResponseCodeInterpreterCallInProgressEvent:
    return ResponseCodeInterpreterCallInProgressEvent.model_construct(
        type="response.code_interpreter_call.in_progress",
        item_id=item_id,
        output_index=0,
        sequence_number=0,
    )


def _interpreting(item_id: str) -> ResponseCodeInterpreterCallInterpretingEvent:
    return ResponseCodeInterpreterCallInterpretingEvent.model_construct(
        type="response.code_interpreter_call.interpreting",
        item_id=item_id,
        output_index=0,
        sequence_number=0,
    )


def _completed(item_id: str) -> ResponseCodeInterpreterCallCompletedEvent:
    return ResponseCodeInterpreterCallCompletedEvent.model_construct(
        type="response.code_interpreter_call.completed",
        item_id=item_id,
        output_index=0,
        sequence_number=0,
    )


@pytest.mark.ai
def test_AI_code_interpreter_event_handler__is_not_appendix_producer():
    """
    Purpose: Code execution must not contribute an assistant-message appendix;
      progress is surfaced only via ``activity_bus``.
    Why this matters: Persisting duplicated code blocks in the saved message
      is redundant with activity/progress UIs and review feedback.
    Setup summary: Instantiate the event handler and assert it does not implement
      :class:`AppendixProducer`.
    """
    event_handler = ResponsesCodeInterpreterEventHandler()
    assert not isinstance(event_handler, AppendixProducer)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_code_interpreter_event_handler__delta__is_ignored():
    """
    Purpose: Code-delta events carry no displayed progress, so they must not
      publish any progress update.
    Why this matters: Progress is driven by the lifecycle events
      (in-progress / interpreting / completed); deltas would only add noise.
    Setup summary: Drive one delta event and assert nothing is published on
      the activity bus.
    """
    event_handler = ResponsesCodeInterpreterEventHandler()
    received: list[ActivityProgressUpdate] = []
    event_handler.activity_bus.subscribe(received.append)

    await event_handler.on_code_interpreter_event(_delta("it-1", "partial"))

    assert received == []


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_code_interpreter_event_handler__in_progress__publishes_triggered_then_detail():
    """
    Purpose: The first (in-progress) event must publish two updates — a
      "Triggered Tool Calls" summary followed by the "Code Execution" detail —
      so a streamed code-execution call renders the same two-step display a
      normal tool call would.
    Why this matters: The summary entry mirrors the orchestrator's
      ``_log_tool_calls`` output; without it the step list would be missing the
      triggered-tool header.
    Setup summary: Drive one in-progress event and assert the ordered pair of
      updates with their distinct correlation ids.
    """
    event_handler = ResponsesCodeInterpreterEventHandler()
    received: list[ActivityProgressUpdate] = []
    event_handler.activity_bus.subscribe(received.append)

    await event_handler.on_code_interpreter_event(_in_progress("it-1"))

    assert len(received) == 2

    triggered, detail = received
    assert triggered.correlation_id == "it-1-triggered"
    assert triggered.status == "COMPLETED"
    assert triggered.text == _TRIGGERED_TEXT

    assert detail.correlation_id == "it-1"
    assert detail.status == "RUNNING"
    assert detail.text == "**Code Execution**\n Writing Code"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_code_interpreter_event_handler__triggered_summary_published_once():
    """
    Purpose: The "Triggered Tool Calls" summary must be published exactly once
      per call, while detail updates continue across the lifecycle.
    Why this matters: The summary is guarded to the in-progress event; later
      events must not re-emit it but must still drive detail transitions.
    Setup summary: Drive in-progress -> interpreting -> completed for one
      ``item_id`` and assert a single triggered update plus one detail update
      per genuine transition.
    """
    event_handler = ResponsesCodeInterpreterEventHandler()
    received: list[ActivityProgressUpdate] = []
    event_handler.activity_bus.subscribe(received.append)

    await event_handler.on_code_interpreter_event(_in_progress("it-1"))
    await event_handler.on_code_interpreter_event(_interpreting("it-1"))
    await event_handler.on_code_interpreter_event(_completed("it-1"))

    triggered = [u for u in received if u.correlation_id == "it-1-triggered"]
    assert len(triggered) == 1

    detail = [u for u in received if u.correlation_id == "it-1"]
    assert [(u.status, u.text) for u in detail] == [
        ("RUNNING", "**Code Execution**\n Writing Code"),
        ("RUNNING", "**Code Execution**\n Executing Code"),
        ("COMPLETED", "**Code Execution**"),
    ]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_code_interpreter_event_handler__detail_deduped_on_repeat():
    """
    Purpose: Repeated events with an unchanged ``(status, text)`` fingerprint
      must not republish.
    Why this matters: Subscribers persist each update as a ``MessageLog`` write;
      duplicate writes for the same state are wasted round-trips.
    Setup summary: Drive interpreting twice for one ``item_id`` and assert a
      single update is published.
    """
    event_handler = ResponsesCodeInterpreterEventHandler()
    received: list[ActivityProgressUpdate] = []
    event_handler.activity_bus.subscribe(received.append)

    await event_handler.on_code_interpreter_event(_interpreting("it-1"))
    await event_handler.on_code_interpreter_event(_interpreting("it-1"))

    assert len(received) == 1
    assert received[0].status == "RUNNING"
    assert received[0].text == "**Code Execution**\n Executing Code"
