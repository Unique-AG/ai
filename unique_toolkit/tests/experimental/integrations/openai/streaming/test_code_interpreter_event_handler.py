"""Tests for ``ResponsesCodeInterpreterEventHandler`` — progress-update dedup."""

from __future__ import annotations

import pytest
from openai.types.responses.response_code_interpreter_call_code_delta_event import (
    ResponseCodeInterpreterCallCodeDeltaEvent,
)
from openai.types.responses.response_code_interpreter_call_in_progress_event import (
    ResponseCodeInterpreterCallInProgressEvent,
)

from unique_toolkit.experimental.components.streaming import (
    ActivityProgressUpdate,
    AppendixProducer,
)
from unique_toolkit.experimental.integrations.openai.streaming.event_routing.responses.code_interpreter_event_handler import (
    ResponsesCodeInterpreterEventHandler,
)


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
async def test_AI_code_interpreter_event_handler__delta__still_publishes_progress_update():
    """
    Purpose: Code-delta events must still publish a ``RUNNING`` progress
      update so subscribers can drive spinners / activity UIs.
    Why this matters: Activity UIs depend on a reliable progress stream
      for code-interpreter runs.
    Setup summary: Drive one delta event and assert exactly one
      :class:`ActivityProgressUpdate` is published on the activity bus
      with ``status == "RUNNING"``.
    """
    event_handler = ResponsesCodeInterpreterEventHandler()
    received: list[ActivityProgressUpdate] = []
    event_handler.activity_bus.subscribe(received.append)

    await event_handler.on_code_interpreter_event(_delta("it-1", "partial"))

    assert len(received) == 1
    assert received[0].status == "RUNNING"
    assert received[0].correlation_id == "it-1"
