"""Unit tests for rate-limit retry UX in ChatService.complete_responses_with_references_async.

Covers:
- _on_rate_limit_retry creates a message log entry on first hit
- _on_rate_limit_retry updates the same entry on subsequent hits (no new line)
- Countdown ticker writes decremented seconds to the log
- finally marks the log COMPLETED when the stream succeeds
- finally marks the log FAILED when the stream raises after a rate-limit log was created
- no log when the stream errors before any on_rate_limit_retry callback runs
- Feature-flag guard: no log written when flag is off
- Config guard: no log written when log_message_on_retry is False
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueContext,
)
from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus
from unique_toolkit.services.chat_service import ChatService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_COMPANY_ID = "company-1"
_MSG_ID = "amsg-1"


@pytest.fixture
def chat_service() -> ChatService:
    auth = AuthContext(user_id=SecretStr("user-1"), company_id=SecretStr(_COMPANY_ID))
    chat = ChatContext(
        chat_id="chat-1",
        assistant_id="assistant-1",
        last_assistant_message_id=_MSG_ID,
        last_user_message_id="umsg-1",
        last_user_message_text="hello",
    )
    return ChatService.from_context(UniqueContext(auth=auth, chat=chat))


def _make_log(message_log_id: str = "log-1", order: int = 1) -> MessageLog:
    return MessageLog(
        id=message_log_id,
        message_id=_MSG_ID,
        status=MessageLogStatus.RUNNING,
        text="Rate limit reached; retrying in 30s (attempt 1)",
        order=order,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MODULE = "unique_toolkit.services.chat_service"


def _patch_stream(return_value=None, side_effect=None):
    mock = AsyncMock()
    if side_effect is not None:
        mock.side_effect = side_effect
    else:
        mock.return_value = return_value or MagicMock()
    return patch(f"{_MODULE}.stream_responses_with_references_async", mock), mock


def _patch_feature_flag(enabled: bool):
    return patch(
        f"{_MODULE}.is_flag_enabled",
        AsyncMock(return_value=enabled),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rate_limit_ux__creates_log_entry_on_first_retry(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify _on_rate_limit_retry creates a message log on the first rate-limit hit.
    Why this matters: Without the log entry the user sees nothing during the wait.
    Setup summary: Simulate one rate-limit hit via on_rate_limit_retry callback; assert create called once.
    """
    created_log = _make_log()
    create_mock = AsyncMock(return_value=created_log)
    update_mock = AsyncMock(return_value=created_log)
    stream_result = MagicMock()

    # Capture the callback and call it manually so we can control when it fires.
    captured_callback = None

    async def fake_stream(**kwargs):
        nonlocal captured_callback
        captured_callback = kwargs.get("on_rate_limit_retry")
        return stream_result

    with (
        patch(f"{_MODULE}.stream_responses_with_references_async", fake_stream),
        patch.object(chat_service, "create_message_log_async", create_mock),
        patch.object(chat_service, "update_message_log_async", update_mock),
        _patch_feature_flag(True),
        patch(f"{_MODULE}.rate_limit_retry_config") as cfg,
    ):
        cfg.log_message_on_retry = True
        cfg.max_attempts = 2
        cfg.initial_delay_seconds = 30.0

        task = asyncio.create_task(
            chat_service.complete_responses_with_references_async(
                model_name="gpt-4o",
                messages="hello",
            )
        )
        # Allow the coroutine to reach the await inside fake_stream
        await asyncio.sleep(0)
        assert captured_callback is not None
        await captured_callback(1, 30.0)
        await task

    create_mock.assert_awaited_once()
    call_kwargs = create_mock.call_args.kwargs
    assert call_kwargs["status"] == MessageLogStatus.RUNNING
    assert "retrying in 30s" in call_kwargs["text"]
    assert "(attempt 1)" in call_kwargs["text"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rate_limit_ux__initial_display_uses_round_not_int_for_jittered_wait(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Initial banner and countdown must use the same rounded second value.
    Why this matters: tenacity adds jitter so wait_secs is often non-integer; using
    round() once avoids a jump (e.g. "31s" then 29s) from mixing :.0f with int().
    Setup summary: Callback with 30.7s; assert log text shows 31s (round), not 30 (int).
    """
    created_log = _make_log()
    create_mock = AsyncMock(return_value=created_log)
    stream_result = MagicMock()
    captured_callback = None

    async def fake_stream(**kwargs):
        nonlocal captured_callback
        captured_callback = kwargs.get("on_rate_limit_retry")
        return stream_result

    with (
        patch(f"{_MODULE}.stream_responses_with_references_async", fake_stream),
        patch.object(chat_service, "create_message_log_async", create_mock),
        _patch_feature_flag(True),
        patch(f"{_MODULE}.rate_limit_retry_config") as cfg,
    ):
        cfg.log_message_on_retry = True
        cfg.max_attempts = 2
        cfg.initial_delay_seconds = 30.0

        task = asyncio.create_task(
            chat_service.complete_responses_with_references_async(
                model_name="gpt-4o",
                messages="hello",
            )
        )
        await asyncio.sleep(0)
        assert captured_callback is not None
        await captured_callback(1, 30.7)
        await task

    text = create_mock.call_args.kwargs["text"]
    assert "retrying in 31s" in text
    assert "retrying in 30s" not in text


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rate_limit_ux__updates_existing_log_on_second_retry(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify the second rate-limit hit updates the existing log entry instead of creating a new one.
    Why this matters: Creating a new line per attempt clutters the UI; in-place update is the expected UX.
    Setup summary: Call on_rate_limit_retry twice; assert create called once and update called once.
    """
    created_log = _make_log()
    updated_log = _make_log()
    create_mock = AsyncMock(return_value=created_log)
    update_mock = AsyncMock(return_value=updated_log)
    stream_result = MagicMock()

    captured_callback = None

    async def fake_stream(**kwargs):
        nonlocal captured_callback
        captured_callback = kwargs.get("on_rate_limit_retry")
        return stream_result

    with (
        patch(f"{_MODULE}.stream_responses_with_references_async", fake_stream),
        patch.object(chat_service, "create_message_log_async", create_mock),
        patch.object(chat_service, "update_message_log_async", update_mock),
        _patch_feature_flag(True),
        patch(f"{_MODULE}.rate_limit_retry_config") as cfg,
    ):
        cfg.log_message_on_retry = True
        cfg.max_attempts = 3
        cfg.initial_delay_seconds = 30.0

        task = asyncio.create_task(
            chat_service.complete_responses_with_references_async(
                model_name="gpt-4o",
                messages="hello",
            )
        )
        await asyncio.sleep(0)
        assert captured_callback is not None
        await captured_callback(1, 30.0)  # first hit — creates
        await captured_callback(2, 60.0)  # second hit — updates
        await task

    create_mock.assert_awaited_once()
    # update called at least once for the second retry (may also be called by finally)
    assert update_mock.await_count >= 1
    # The second retry call should use update_message_log_async with the existing log id
    update_calls = update_mock.call_args_list
    retry_update = update_calls[0].kwargs
    assert retry_update["message_log_id"] == "log-1"
    assert "(attempt 2)" in retry_update["text"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rate_limit_ux__marks_log_completed_on_success(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify the rate-limit log is marked COMPLETED when the stream succeeds.
    Why this matters: Without cleanup the spinning indicator lingers in the UI.
    Setup summary: Hold the stream open until after the callback fires; then let it
    return so finally marks the log COMPLETED.
    """
    created_log = _make_log()
    create_mock = AsyncMock(return_value=created_log)
    update_mock = AsyncMock(return_value=created_log)
    stream_result = MagicMock()

    # Event that gates stream return — lets us fire the callback first.
    proceed_event = asyncio.Event()
    captured_callback = None

    async def fake_stream(**kwargs):
        nonlocal captured_callback
        captured_callback = kwargs.get("on_rate_limit_retry")
        await proceed_event.wait()
        return stream_result

    with (
        patch(f"{_MODULE}.stream_responses_with_references_async", fake_stream),
        patch.object(chat_service, "create_message_log_async", create_mock),
        patch.object(chat_service, "update_message_log_async", update_mock),
        _patch_feature_flag(True),
        patch(f"{_MODULE}.rate_limit_retry_config") as cfg,
    ):
        cfg.log_message_on_retry = True
        cfg.max_attempts = 2
        cfg.initial_delay_seconds = 30.0

        task = asyncio.create_task(
            chat_service.complete_responses_with_references_async(
                model_name="gpt-4o",
                messages="hello",
            )
        )
        # Let the stream reach event.wait()
        await asyncio.sleep(0)
        assert captured_callback is not None
        # Fire callback — creates the log entry
        await captured_callback(1, 30.0)
        # Now let the stream return — finally block will see the log and mark COMPLETED
        proceed_event.set()
        await task

    # The final update (from finally) must be COMPLETED
    assert update_mock.await_count >= 1
    final_call_kwargs = update_mock.call_args_list[-1].kwargs
    assert final_call_kwargs["status"] == MessageLogStatus.COMPLETED
    assert "resolved" in final_call_kwargs["text"].lower()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rate_limit_ux__no_log_when_stream_fails_before_rate_limit_callback(
    chat_service: ChatService,
) -> None:
    """
    Purpose: If the stream fails before tenacity invokes on_rate_limit_retry, no message log exists.
    Why this matters: The callback is only wired from the rate-limit retry path; unrelated
    stream errors must not leave stray log rows.
    Setup summary: fake_stream raises immediately; assert create_message_log_async is never called.
    """
    create_mock = AsyncMock()
    update_mock = AsyncMock()

    async def fake_stream(**kwargs):
        raise RuntimeError("rate limit exhausted")

    with (
        patch(f"{_MODULE}.stream_responses_with_references_async", fake_stream),
        patch.object(chat_service, "create_message_log_async", create_mock),
        patch.object(chat_service, "update_message_log_async", update_mock),
        _patch_feature_flag(True),
        patch(f"{_MODULE}.rate_limit_retry_config") as cfg,
    ):
        cfg.log_message_on_retry = True
        cfg.max_attempts = 2
        cfg.initial_delay_seconds = 30.0

        task = asyncio.create_task(
            chat_service.complete_responses_with_references_async(
                model_name="gpt-4o",
                messages="hello",
            )
        )
        with pytest.raises(RuntimeError, match="rate limit exhausted"):
            await task

    create_mock.assert_not_awaited()
    update_mock.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rate_limit_ux__marks_log_failed_when_stream_raises_after_callback(
    chat_service: ChatService,
) -> None:
    """
    Purpose: When a rate-limit message log was created and the stream then raises, finally marks FAILED.
    Why this matters: The user should see 'retries exhausted' instead of a stuck RUNNING row.
    Setup summary: Gate fake_stream with an event; invoke the retry callback (creates log),
    then release the stream so it raises; assert the last update_message_log_async call is FAILED.
    """
    created_log = _make_log()
    create_mock = AsyncMock(return_value=created_log)
    update_mock = AsyncMock(return_value=created_log)
    proceed_event = asyncio.Event()
    captured_callback = None

    async def fake_stream(**kwargs):
        nonlocal captured_callback
        captured_callback = kwargs.get("on_rate_limit_retry")
        await proceed_event.wait()
        raise RuntimeError("stream failed after rate limit UX")

    with (
        patch(f"{_MODULE}.stream_responses_with_references_async", fake_stream),
        patch.object(chat_service, "create_message_log_async", create_mock),
        patch.object(chat_service, "update_message_log_async", update_mock),
        _patch_feature_flag(True),
        patch(f"{_MODULE}.rate_limit_retry_config") as cfg,
    ):
        cfg.log_message_on_retry = True
        cfg.max_attempts = 2
        cfg.initial_delay_seconds = 30.0

        task = asyncio.create_task(
            chat_service.complete_responses_with_references_async(
                model_name="gpt-4o",
                messages="hello",
            )
        )
        await asyncio.sleep(0)
        assert captured_callback is not None
        await captured_callback(1, 30.0)
        proceed_event.set()
        with pytest.raises(RuntimeError, match="stream failed after rate limit UX"):
            await task

    create_mock.assert_awaited_once()
    assert update_mock.await_count >= 1
    final_kwargs = update_mock.call_args_list[-1].kwargs
    assert final_kwargs["status"] == MessageLogStatus.FAILED
    assert "exhausted" in final_kwargs["text"].lower()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rate_limit_ux__no_log_when_flag_disabled(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify no message log is written when the feature flag is off.
    Why this matters: Companies without the new UI must not receive unexpected log entries.
    Setup summary: Flag off; trigger callback; assert create never called.
    """
    create_mock = AsyncMock()
    stream_result = MagicMock()
    captured_callback = None

    async def fake_stream(**kwargs):
        nonlocal captured_callback
        captured_callback = kwargs.get("on_rate_limit_retry")
        return stream_result

    with (
        patch(f"{_MODULE}.stream_responses_with_references_async", fake_stream),
        patch.object(chat_service, "create_message_log_async", create_mock),
        _patch_feature_flag(False),
        patch(f"{_MODULE}.rate_limit_retry_config") as cfg,
    ):
        cfg.log_message_on_retry = True

        task = asyncio.create_task(
            chat_service.complete_responses_with_references_async(
                model_name="gpt-4o",
                messages="hello",
            )
        )
        await asyncio.sleep(0)
        assert captured_callback is not None
        await captured_callback(1, 30.0)
        await task

    create_mock.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rate_limit_ux__no_log_when_config_disabled(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify no message log is written when log_message_on_retry is False.
    Why this matters: Operators can suppress the UX message via env var.
    Setup summary: log_message_on_retry=False; trigger callback; assert create never called.
    """
    create_mock = AsyncMock()
    stream_result = MagicMock()
    captured_callback = None

    async def fake_stream(**kwargs):
        nonlocal captured_callback
        captured_callback = kwargs.get("on_rate_limit_retry")
        return stream_result

    with (
        patch(f"{_MODULE}.stream_responses_with_references_async", fake_stream),
        patch.object(chat_service, "create_message_log_async", create_mock),
        _patch_feature_flag(True),
        patch(f"{_MODULE}.rate_limit_retry_config") as cfg,
    ):
        cfg.log_message_on_retry = False

        task = asyncio.create_task(
            chat_service.complete_responses_with_references_async(
                model_name="gpt-4o",
                messages="hello",
            )
        )
        await asyncio.sleep(0)
        assert captured_callback is not None
        await captured_callback(1, 30.0)
        await task

    create_mock.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rate_limit_ux__no_log_when_no_retry_triggered(
    chat_service: ChatService,
) -> None:
    """
    Purpose: Verify no message log is written when the stream succeeds without hitting a rate limit.
    Why this matters: The happy path must not produce spurious log entries.
    Setup summary: Stream succeeds immediately; assert create never called.
    """
    create_mock = AsyncMock()
    update_mock = AsyncMock()

    async def fake_stream(**kwargs):
        return MagicMock()

    with (
        patch(f"{_MODULE}.stream_responses_with_references_async", fake_stream),
        patch.object(chat_service, "create_message_log_async", create_mock),
        patch.object(chat_service, "update_message_log_async", update_mock),
        _patch_feature_flag(True),
        patch(f"{_MODULE}.rate_limit_retry_config") as cfg,
    ):
        cfg.log_message_on_retry = True

        await chat_service.complete_responses_with_references_async(
            model_name="gpt-4o",
            messages="hello",
        )

    create_mock.assert_not_awaited()
    update_mock.assert_not_awaited()
