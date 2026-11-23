"""Tests for the stop-on-abandon wait in chat_in_space (UN-30319)."""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.utils.chat_in_space import (
    MessageWaitTimeoutError,
    send_message_and_wait_for_completion,
    wait_for_message_completion,
)

pytestmark = pytest.mark.ai

_RUNNING = {
    "id": "assistant-msg",
    "chatId": "chat-1",
    "role": "ASSISTANT",
    "text": None,
    "completedAt": None,
    "stoppedStreamingAt": None,
}
_FINISHED = {**_RUNNING, "text": "done", "stoppedStreamingAt": "2026-01-01T00:00:00Z"}
_MODULE = "unique_sdk.utils.chat_in_space"


@contextmanager
def _platform(*, latest: object, stop: AsyncMock) -> Iterator[None]:
    latest_kwargs = (
        {"side_effect": latest} if callable(latest) else {"return_value": latest}
    )
    with (
        patch(
            f"{_MODULE}.Space.create_message_async",
            new_callable=AsyncMock,
            return_value={"id": "user-msg", "chatId": "chat-1"},
        ),
        patch(
            f"{_MODULE}.Space.get_latest_message_async",
            new_callable=AsyncMock,
            **latest_kwargs,
        ),
        patch(
            f"{_MODULE}.Message.retrieve_async",
            new_callable=AsyncMock,
            return_value={"debugInfo": None},
        ),
        patch(f"{_MODULE}.Message.stop_async", stop),
    ):
        yield


async def _wait(*, stop_on_abandon: bool, max_wait: float = 0.03) -> object:
    return await wait_for_message_completion(
        user_id="user-1",
        company_id="company-1",
        chat_id="chat-1",
        message_id="user-msg",
        poll_interval=0.01,
        max_wait=max_wait,
        stop_on_abandon=stop_on_abandon,
    )


async def test_wait__turn_finishes__returns_answer_without_stop() -> None:
    stop = AsyncMock()
    with _platform(latest=_FINISHED, stop=stop):
        answer = await _wait(stop_on_abandon=True)

    assert answer["text"] == "done"
    stop.assert_not_awaited()


async def test_wait__max_wait_reached__stops_turn_and_reports_it() -> None:
    stop = AsyncMock()
    with _platform(latest=_RUNNING, stop=stop):
        with pytest.raises(MessageWaitTimeoutError) as raised:
            _ = await _wait(stop_on_abandon=True)

    stop.assert_awaited_once_with("user-1", "company-1", "user-msg", chatId="chat-1")
    assert raised.value.turn_stopped is True
    assert raised.value.chat_id == "chat-1"
    assert raised.value.message_id == "user-msg"


async def test_wait__max_wait_reached__stays_a_timeout_error_with_the_old_text() -> (
    None
):
    with _platform(latest=_RUNNING, stop=AsyncMock()):
        with pytest.raises(
            TimeoutError, match="Timed out waiting for prompt completion."
        ):
            _ = await _wait(stop_on_abandon=False)


async def test_wait__max_wait_reached_without_opt_in__leaves_turn_running() -> None:
    stop = AsyncMock()
    with _platform(latest=_RUNNING, stop=stop):
        with pytest.raises(MessageWaitTimeoutError) as raised:
            _ = await _wait(stop_on_abandon=False)

    stop.assert_not_awaited()
    assert raised.value.turn_stopped is False


async def test_wait__stop_fails__reports_turn_not_stopped() -> None:
    stop = AsyncMock(side_effect=RuntimeError("boom"))
    with _platform(latest=_RUNNING, stop=stop):
        with pytest.raises(MessageWaitTimeoutError) as raised:
            _ = await _wait(stop_on_abandon=True)

    assert raised.value.turn_stopped is False


async def test_wait__cancelled__stops_turn_before_the_cancellation_leaves() -> None:
    stop = AsyncMock()
    with _platform(latest=_RUNNING, stop=stop):
        waiting = asyncio.ensure_future(_wait(stop_on_abandon=True, max_wait=60))
        await asyncio.sleep(0.03)
        _ = waiting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiting

    stop.assert_awaited_once_with("user-1", "company-1", "user-msg", chatId="chat-1")


async def test_wait__cancelled_again_during_stop__stop_still_completes() -> None:
    stop_started = asyncio.Event()
    release_stop = asyncio.Event()
    stop_finished = asyncio.Event()

    async def slow_stop(*_args: object, **_kwargs: object) -> None:
        stop_started.set()
        _ = await release_stop.wait()
        stop_finished.set()

    with _platform(latest=_RUNNING, stop=AsyncMock(side_effect=slow_stop)):
        waiting = asyncio.ensure_future(_wait(stop_on_abandon=True, max_wait=60))
        await asyncio.sleep(0.03)
        _ = waiting.cancel()
        _ = await stop_started.wait()
        _ = waiting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiting
        release_stop.set()
        async with asyncio.timeout(1):
            _ = await stop_finished.wait()


async def test_wait__poll_fails__stops_turn_and_raises_the_poll_error() -> None:
    stop = AsyncMock()

    async def failing_poll(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("poll failed")

    with _platform(latest=failing_poll, stop=stop):
        with pytest.raises(RuntimeError, match="poll failed"):
            _ = await _wait(stop_on_abandon=True)

    stop.assert_awaited_once()


async def test_send_and_wait__stop_on_abandon__stops_the_posted_message() -> None:
    stop = AsyncMock()
    with _platform(latest=_RUNNING, stop=stop):
        with pytest.raises(MessageWaitTimeoutError):
            _ = await send_message_and_wait_for_completion(
                user_id="user-1",
                company_id="company-1",
                assistant_id="assistant-1",
                text="hello",
                poll_interval=0.01,
                max_wait=0.03,
                stop_on_abandon=True,
            )

    stop.assert_awaited_once_with("user-1", "company-1", "user-msg", chatId="chat-1")


async def test_send_and_wait__on_message_created__gets_posted_message_before_wait() -> (
    None
):
    seen: list[object] = []

    async def on_message_created(message: object) -> None:
        seen.append(message)

    with _platform(latest=_FINISHED, stop=AsyncMock()):
        _ = await send_message_and_wait_for_completion(
            user_id="user-1",
            company_id="company-1",
            assistant_id="assistant-1",
            text="hello",
            poll_interval=0.01,
            max_wait=0.03,
            on_message_created=on_message_created,
        )

    assert seen == [{"id": "user-msg", "chatId": "chat-1"}]
