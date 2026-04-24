"""Tests for ``ResponsesCodeInterpreterHandler`` — progress-update dedup
and done-only code accumulation strategy.
"""

from __future__ import annotations

import pytest
from openai.types.responses.response_code_interpreter_call_code_delta_event import (
    ResponseCodeInterpreterCallCodeDeltaEvent,
)
from openai.types.responses.response_code_interpreter_call_code_done_event import (
    ResponseCodeInterpreterCallCodeDoneEvent,
)
from openai.types.responses.response_code_interpreter_call_in_progress_event import (
    ResponseCodeInterpreterCallInProgressEvent,
)

from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses.code_interpreter_handler import (
    ResponsesCodeInterpreterHandler,
)
from unique_toolkit.protocols.streaming import ActivityProgressUpdate


def _delta(item_id: str, text: str) -> ResponseCodeInterpreterCallCodeDeltaEvent:
    return ResponseCodeInterpreterCallCodeDeltaEvent.model_construct(
        type="response.code_interpreter_call_code.delta",
        item_id=item_id,
        output_index=0,
        delta=text,
        sequence_number=0,
    )


def _done(item_id: str, code: str) -> ResponseCodeInterpreterCallCodeDoneEvent:
    return ResponseCodeInterpreterCallCodeDoneEvent.model_construct(
        type="response.code_interpreter_call_code.done",
        item_id=item_id,
        output_index=0,
        code=code,
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
@pytest.mark.asyncio
async def test_AI_code_interpreter_handler__deltas_only__produce_no_appendix():
    """
    Purpose: Deltas on their own must not populate the code appendix — the
      handler uses the done-only strategy for code accumulation.
    Why this matters: The previous dual strategy (``_code += delta`` plus
      ``_code = event.code`` on done) relied on an undocumented provider
      ordering that could duplicate or truncate the appendix if deltas
      arrived after done (or out of order). Done-only removes the coupling.
    Setup summary: Drive several delta events, never a done event, and
      assert ``get_appendix()`` returns ``None``.
    """
    handler = ResponsesCodeInterpreterHandler()
    await handler.on_code_interpreter_event(_in_progress("it-1"))
    await handler.on_code_interpreter_event(_delta("it-1", "print(1)\n"))
    await handler.on_code_interpreter_event(_delta("it-1", "print(2)\n"))

    assert handler.get_appendix() is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_code_interpreter_handler__done__snapshots_full_code_from_event():
    """
    Purpose: The terminating done event carries the full assembled code; the
      appendix must reflect exactly that payload regardless of what deltas
      were observed before.
    Why this matters: Done-only avoids any drift between streamed deltas and
      the authoritative final code string shipped on done.
    Setup summary: Drive deltas with partial/wrong text, then a done event
      with the authoritative code, and assert the appendix matches.
    """
    handler = ResponsesCodeInterpreterHandler()
    await handler.on_code_interpreter_event(_delta("it-1", "noise-"))
    await handler.on_code_interpreter_event(_delta("it-1", "more noise-"))
    await handler.on_code_interpreter_event(_done("it-1", "print('final')"))

    appendix = handler.get_appendix()
    assert appendix is not None
    assert "print('final')" in appendix
    assert "noise-" not in appendix


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_code_interpreter_handler__delta__still_publishes_progress_update():
    """
    Purpose: Code-delta events must still publish a ``RUNNING`` progress
      update so subscribers can drive spinners / activity UIs.
    Why this matters: Switching to done-only accumulation must not
      regress the observable progress stream.
    Setup summary: Drive one delta event and assert exactly one
      :class:`ActivityProgressUpdate` is published on the activity bus
      with ``status == "RUNNING"``.
    """
    handler = ResponsesCodeInterpreterHandler()
    received: list[ActivityProgressUpdate] = []
    handler.activity_bus.subscribe(received.append)

    await handler.on_code_interpreter_event(_delta("it-1", "partial"))

    assert len(received) == 1
    assert received[0].status == "RUNNING"
    assert received[0].correlation_id == "it-1"
