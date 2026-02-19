import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from unique_toolkit.chat.cancellation import CancellationEvent, CancellationWatcher


def _make_watcher() -> CancellationWatcher:
    return CancellationWatcher(
        user_id="u1",
        company_id="c1",
        chat_id="chat1",
        assistant_message_id="msg1",
    )


class TestProperties:
    def test_is_cancelled__initially_false(self):
        w = _make_watcher()
        assert w.is_cancelled is False

    def test_on_cancellation__returns_bus(self):
        w = _make_watcher()
        assert w.on_cancellation is w._bus


class TestCheckCancellationAsync:
    @pytest.mark.asyncio
    @patch("unique_sdk.Message.retrieve_async", new_callable=AsyncMock)
    async def test_returns_false__when_not_cancelled(self, mock_retrieve):
        mock_retrieve.return_value = SimpleNamespace(cancelledAt=None)
        w = _make_watcher()

        result = await w.check_cancellation_async()

        assert result is False
        assert w.is_cancelled is False

    @pytest.mark.asyncio
    @patch("unique_sdk.Message.retrieve_async", new_callable=AsyncMock)
    async def test_returns_true__when_cancelled(self, mock_retrieve):
        mock_retrieve.return_value = SimpleNamespace(cancelledAt="2025-01-01T00:00:00Z")
        w = _make_watcher()

        result = await w.check_cancellation_async()

        assert result is True
        assert w.is_cancelled is True

    @pytest.mark.asyncio
    @patch("unique_sdk.Message.retrieve_async", new_callable=AsyncMock)
    async def test_notifies_subscribers(self, mock_retrieve):
        mock_retrieve.return_value = SimpleNamespace(cancelledAt="2025-01-01T00:00:00Z")
        w = _make_watcher()
        received: list[CancellationEvent] = []
        w.on_cancellation.subscribe(lambda e: received.append(e))

        await w.check_cancellation_async()

        assert len(received) == 1
        assert received[0].message_id == "msg1"

    @pytest.mark.asyncio
    async def test_returns_true_immediately__when_already_cancelled(self):
        w = _make_watcher()
        w._cancelled = True

        result = await w.check_cancellation_async()
        assert result is True

    @pytest.mark.asyncio
    @patch("unique_sdk.Message.retrieve_async", new_callable=AsyncMock)
    async def test_returns_false__on_exception(self, mock_retrieve):
        mock_retrieve.side_effect = RuntimeError("connection error")
        w = _make_watcher()

        result = await w.check_cancellation_async()

        assert result is False
        assert w.is_cancelled is False


class TestCheckCancellationSync:
    @patch("unique_sdk.Message.retrieve")
    def test_returns_false__when_not_cancelled(self, mock_retrieve):
        mock_retrieve.return_value = SimpleNamespace(cancelledAt=None)
        w = _make_watcher()

        assert w.check_cancellation() is False
        assert w.is_cancelled is False

    @patch("unique_sdk.Message.retrieve")
    def test_returns_true__when_cancelled(self, mock_retrieve):
        mock_retrieve.return_value = SimpleNamespace(cancelledAt="2025-01-01T00:00:00Z")
        w = _make_watcher()

        assert w.check_cancellation() is True
        assert w.is_cancelled is True

    def test_returns_true_immediately__when_already_cancelled(self):
        w = _make_watcher()
        w._cancelled = True
        assert w.check_cancellation() is True

    @patch("unique_sdk.Message.retrieve")
    def test_returns_false__on_exception(self, mock_retrieve):
        mock_retrieve.side_effect = RuntimeError("connection error")
        w = _make_watcher()

        assert w.check_cancellation() is False

    @pytest.mark.asyncio
    @patch("unique_sdk.Message.retrieve")
    async def test_notifies_subscribers__when_loop_running(self, mock_retrieve):
        mock_retrieve.return_value = SimpleNamespace(cancelledAt="2025-01-01T00:00:00Z")
        w = _make_watcher()
        received: list[CancellationEvent] = []
        w.on_cancellation.subscribe(lambda e: received.append(e))

        w.check_cancellation()
        await asyncio.sleep(0)

        assert len(received) == 1
        assert received[0].message_id == "msg1"


class TestRunWithCancellation:
    @pytest.mark.asyncio
    @patch("unique_sdk.Message.retrieve_async", new_callable=AsyncMock)
    async def test_returns_coroutine_result__when_not_cancelled(self, mock_retrieve):
        mock_retrieve.return_value = SimpleNamespace(cancelledAt=None)
        w = _make_watcher()

        async def work():
            return 42

        result = await w.run_with_cancellation(work(), poll_interval=0.05)
        assert result == 42

    @pytest.mark.asyncio
    async def test_returns_cancel_result__when_cancelled(self):
        w = _make_watcher()

        check_count = 0

        async def mock_check():
            nonlocal check_count
            check_count += 1
            if check_count >= 1:
                w._cancelled = True
                event = CancellationEvent(message_id="msg1")
                await w._bus.publish_and_wait_async(event)
                return True
            return False

        w.check_cancellation_async = mock_check  # type: ignore[assignment]

        async def slow_work():
            await asyncio.sleep(10)
            return "should not reach"

        result = await w.run_with_cancellation(
            slow_work(), poll_interval=0.01, cancel_result="stopped"
        )
        assert result == "stopped"
        assert w.is_cancelled is True

    @pytest.mark.asyncio
    async def test_returns_none_by_default__when_cancelled(self):
        w = _make_watcher()

        async def mock_check():
            w._cancelled = True
            event = CancellationEvent(message_id="msg1")
            await w._bus.publish_and_wait_async(event)
            return True

        w.check_cancellation_async = mock_check  # type: ignore[assignment]

        async def slow_work():
            await asyncio.sleep(10)

        result = await w.run_with_cancellation(slow_work(), poll_interval=0.01)
        assert result is None
