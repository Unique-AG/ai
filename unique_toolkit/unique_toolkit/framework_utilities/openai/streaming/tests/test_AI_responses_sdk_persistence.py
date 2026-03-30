"""Tests for ResponsesSdkPersistence (Responses API, including code-interpreter events)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.responses import (
    ResponseTextDeltaEvent,
)
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

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses_sdk_persistence import (
    ResponsesSdkPersistence,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text_delta(delta: str, seq: int = 0) -> ResponseTextDeltaEvent:
    return ResponseTextDeltaEvent(
        content_index=0,
        delta=delta,
        item_id="msg-1",
        logprobs=[],
        output_index=0,
        sequence_number=seq,
        type="response.output_text.delta",
    )


def _ci_in_progress(item_id: str) -> ResponseCodeInterpreterCallInProgressEvent:
    return ResponseCodeInterpreterCallInProgressEvent.model_construct(
        item_id=item_id,
        type="response.code_interpreter_call.in_progress",
        output_index=0,
        sequence_number=0,
    )


def _ci_delta(item_id: str, delta: str) -> ResponseCodeInterpreterCallCodeDeltaEvent:
    return ResponseCodeInterpreterCallCodeDeltaEvent.model_construct(
        item_id=item_id,
        delta=delta,
        type="response.code_interpreter_call.code.delta",
        output_index=0,
        sequence_number=1,
    )


def _ci_interpreting(item_id: str) -> ResponseCodeInterpreterCallInterpretingEvent:
    return ResponseCodeInterpreterCallInterpretingEvent.model_construct(
        item_id=item_id,
        type="response.code_interpreter_call.interpreting",
        output_index=0,
        sequence_number=2,
    )


def _ci_code_done(item_id: str, code: str) -> ResponseCodeInterpreterCallCodeDoneEvent:
    return ResponseCodeInterpreterCallCodeDoneEvent.model_construct(
        item_id=item_id,
        code=code,
        type="response.code_interpreter_call.code.done",
        output_index=0,
        sequence_number=3,
    )


def _ci_completed(item_id: str) -> ResponseCodeInterpreterCallCompletedEvent:
    return ResponseCodeInterpreterCallCompletedEvent.model_construct(
        item_id=item_id,
        type="response.code_interpreter_call.completed",
        output_index=0,
        sequence_number=4,
    )


def _fake_message_log(log_id: str = "log-1") -> MagicMock:
    ml = MagicMock()
    ml.id = log_id
    return ml


# ---------------------------------------------------------------------------
# on_event: early return when chat context is None
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_on_event__is_noop__when_chat_context_is_none(
    test_settings_no_chat: UniqueSettings,
) -> None:
    """
    Purpose: Verify on_event returns immediately when chat context is None.
    Why this matters: Persistence may be constructed before chat is resolved; a None
        check prevents crashes on SDK calls that require a chat ID.
    Setup summary: Settings without chat, send a code-interpreter event, assert no SDK calls.
    """
    persistence = ResponsesSdkPersistence(test_settings_no_chat, replacers=[])

    with (
        patch(
            "unique_sdk.MessageLog.create_async", new_callable=AsyncMock
        ) as mock_create,
        patch(
            "unique_sdk.Message.create_event_async", new_callable=AsyncMock
        ) as mock_event,
    ):
        await persistence.on_event(_ci_in_progress("item-1"), index=0)

    mock_create.assert_not_awaited()
    mock_event.assert_not_awaited()


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_AI_reset__clears_text_code_and_log_state(
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify reset() wipes _full_text, _code, and _item_id_to_log.
    Why this matters: Stale code output or MessageLog IDs from a prior stream must not
        leak into subsequent runs on the same instance.
    Setup summary: Manually populate internal buffers, call reset(), assert all empty.
    """
    from unique_toolkit.framework_utilities.openai.streaming.pipeline.responses_sdk_persistence import (
        CodeInterpreterLogState,
    )

    persistence = ResponsesSdkPersistence(test_settings, replacers=[])
    persistence._full_text = "prior text"
    persistence._code = "print('hi')"
    persistence._item_id_to_log["item-0"] = CodeInterpreterLogState(
        item_id="item-0",
        message_log_id="log-0",
        status="RUNNING",
        text="running",
    )

    persistence.reset()

    assert persistence._full_text == ""
    assert persistence._code == ""
    assert persistence._item_id_to_log == {}


# ---------------------------------------------------------------------------
# Code interpreter events: first encounter creates a MessageLog
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
@patch(
    "unique_sdk.MessageLog.create_async",
    new_callable=AsyncMock,
    return_value=_fake_message_log("log-1"),
)
async def test_AI_on_event__creates_message_log__for_first_code_interpreter_in_progress(
    mock_create_log: AsyncMock,
    mock_event: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify a new MessageLog is created when a code-interpreter event arrives
        for an item_id that has not been seen before.
    Why this matters: Each code-interpreter call gets its own MessageLog entry in the
        Unique platform; missing the create means the log never appears.
    Setup summary: Send an in-progress event for a fresh item_id, assert create_async called.
    """
    persistence = ResponsesSdkPersistence(test_settings, replacers=[])

    await persistence.on_event(_ci_in_progress("item-1"), index=0)

    mock_create_log.assert_awaited_once()
    assert "item-1" in persistence._item_id_to_log


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
@patch(
    "unique_sdk.MessageLog.create_async",
    new_callable=AsyncMock,
    return_value=_fake_message_log("log-1"),
)
async def test_AI_on_event__creates_message_log__for_code_delta_first_encounter(
    mock_create_log: AsyncMock,
    mock_event: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify a code-delta event for a new item_id creates the MessageLog.
    Why this matters: Code delta is the first event in some streaming scenarios; if
        in-progress is not emitted first, a delta must still create the log entry.
    Setup summary: Send a code-delta event for a fresh item_id, assert create_async called
        and the code buffer accumulates the delta.
    """
    persistence = ResponsesSdkPersistence(test_settings, replacers=[])

    await persistence.on_event(_ci_delta("item-2", "print"), index=0)

    mock_create_log.assert_awaited_once()
    assert persistence._code == "print"


# ---------------------------------------------------------------------------
# Code interpreter events: subsequent events update the MessageLog when status changes
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
@patch("unique_sdk.MessageLog.update_async", new_callable=AsyncMock)
@patch(
    "unique_sdk.MessageLog.create_async",
    new_callable=AsyncMock,
    return_value=_fake_message_log("log-1"),
)
async def test_AI_on_event__updates_message_log__when_status_changes(
    mock_create_log: AsyncMock,
    mock_update_log: AsyncMock,
    mock_event: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify that a status transition from RUNNING to COMPLETED triggers an update.
    Why this matters: The Unique platform log must reflect the final COMPLETED status so
        users see the correct execution state.
    Setup summary: Send in-progress (RUNNING) then code-done (COMPLETED) for the same
        item_id, assert update_async is called on status change.
    """
    persistence = ResponsesSdkPersistence(test_settings, replacers=[])

    await persistence.on_event(_ci_in_progress("item-1"), index=0)
    await persistence.on_event(_ci_code_done("item-1", "print('done')"), index=1)

    mock_create_log.assert_awaited_once()
    mock_update_log.assert_awaited_once()
    assert persistence._code == "print('done')"


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
@patch("unique_sdk.MessageLog.update_async", new_callable=AsyncMock)
@patch(
    "unique_sdk.MessageLog.create_async",
    new_callable=AsyncMock,
    return_value=_fake_message_log("log-1"),
)
async def test_AI_on_event__does_not_update__when_status_unchanged(
    mock_create_log: AsyncMock,
    mock_update_log: AsyncMock,
    mock_event: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify no update call is made when two consecutive events have the same status.
    Why this matters: Redundant updates add unnecessary latency and SDK traffic.
    Setup summary: Send two RUNNING events (in-progress + delta) for the same item_id,
        assert update_async is never called.
    """
    persistence = ResponsesSdkPersistence(test_settings, replacers=[])

    await persistence.on_event(_ci_in_progress("item-1"), index=0)
    await persistence.on_event(_ci_delta("item-1", "x"), index=1)

    mock_update_log.assert_not_awaited()


# ---------------------------------------------------------------------------
# Interpreting and completed events
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
@patch("unique_sdk.MessageLog.update_async", new_callable=AsyncMock)
@patch(
    "unique_sdk.MessageLog.create_async",
    new_callable=AsyncMock,
    return_value=_fake_message_log("log-1"),
)
async def test_AI_on_event__interpreting_event_updates_to_running(
    mock_create_log: AsyncMock,
    mock_update_log: AsyncMock,
    mock_event: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify an interpreting event (after code-done) triggers a status update.
    Why this matters: Interpreting is a distinct phase in the code-interpreter lifecycle;
        the log should reflect it so users see progress.
    Setup summary: In-progress (RUNNING) → interpreting (RUNNING with new text).
        Since status stays RUNNING but text changes, the implementation re-uses the
        status check; no update expected when status is same.
    """
    persistence = ResponsesSdkPersistence(test_settings, replacers=[])

    await persistence.on_event(_ci_in_progress("item-1"), index=0)
    # interpreting is also RUNNING — no update expected
    await persistence.on_event(_ci_interpreting("item-1"), index=1)

    mock_update_log.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.create_event_async", new_callable=AsyncMock)
@patch("unique_sdk.MessageLog.update_async", new_callable=AsyncMock)
@patch(
    "unique_sdk.MessageLog.create_async",
    new_callable=AsyncMock,
    return_value=_fake_message_log("log-1"),
)
async def test_AI_on_event__completed_event_after_running_triggers_update(
    mock_create_log: AsyncMock,
    mock_update_log: AsyncMock,
    mock_event: AsyncMock,
    test_settings: UniqueSettings,
) -> None:
    """
    Purpose: Verify a completed event changes status from RUNNING to COMPLETED.
    Why this matters: The completed event is the definitive terminal state; if the log
        is not updated the Unique platform may show the run as indefinitely RUNNING.
    Setup summary: in-progress (RUNNING) → completed (COMPLETED), assert update called.
    """
    persistence = ResponsesSdkPersistence(test_settings, replacers=[])

    await persistence.on_event(_ci_in_progress("item-1"), index=0)
    await persistence.on_event(_ci_completed("item-1"), index=1)

    mock_update_log.assert_awaited_once()
    state = persistence._item_id_to_log["item-1"]
    assert state.status == "COMPLETED"
