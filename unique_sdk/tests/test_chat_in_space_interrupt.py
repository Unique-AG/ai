"""Tests for the interruptible wait in chat_in_space (UN-30320)."""

from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.utils.chat_in_space import (
    MessageWaitInterruptedError,
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
    with (
        patch(
            f"{_MODULE}.Space.create_message_async",
            new_callable=AsyncMock,
            return_value={"id": "user-msg", "chatId": "chat-1"},
        ),
        patch(
            f"{_MODULE}.Space.get_latest_message_async",
            new_callable=AsyncMock,
            return_value=latest,
        ),
        patch(
            f"{_MODULE}.Message.retrieve_async",
            new_callable=AsyncMock,
            return_value={"debugInfo": None},
        ),
        patch(f"{_MODULE}.Message.stop_async", stop),
    ):
        yield


async def _wait(*, interrupt: AsyncMock) -> object:
    return await wait_for_message_completion(
        user_id="user-1",
        company_id="company-1",
        chat_id="chat-1",
        message_id="user-msg",
        poll_interval=0.01,
        max_wait=0.05,
        stop_on_abandon=True,
        interrupt=interrupt,
    )


async def test_wait__interrupt_fires__raises_and_leaves_the_turn_running() -> None:
    stop = AsyncMock()
    interrupt = AsyncMock(side_effect=[False, True])
    with _platform(latest=_RUNNING, stop=stop):
        with pytest.raises(MessageWaitInterruptedError) as raised:
            _ = await _wait(interrupt=interrupt)

    stop.assert_not_awaited()
    assert raised.value.chat_id == "chat-1"
    assert raised.value.message_id == "user-msg"
    assert interrupt.await_count == 2


async def test_wait__turn_already_finished__answer_wins_over_interrupt() -> None:
    stop = AsyncMock()
    interrupt = AsyncMock(return_value=True)
    with _platform(latest=_FINISHED, stop=stop):
        answer = await _wait(interrupt=interrupt)

    assert answer["text"] == "done"
    interrupt.assert_not_awaited()


async def test_wait__interrupt_check_fails__stops_the_turn_like_any_error() -> None:
    stop = AsyncMock()
    interrupt = AsyncMock(side_effect=RuntimeError("lookup failed"))
    with _platform(latest=_RUNNING, stop=stop):
        with pytest.raises(RuntimeError):
            _ = await _wait(interrupt=interrupt)

    stop.assert_awaited_once()


async def test_send__interrupt_fires__raises_without_stopping_the_turn() -> None:
    stop = AsyncMock()
    with _platform(latest=_RUNNING, stop=stop):
        with pytest.raises(MessageWaitInterruptedError):
            _ = await send_message_and_wait_for_completion(
                user_id="user-1",
                company_id="company-1",
                assistant_id="assistant-1",
                text="hi",
                poll_interval=0.01,
                max_wait=0.05,
                stop_on_abandon=True,
                interrupt=AsyncMock(return_value=True),
            )

    stop.assert_not_awaited()
