"""Tests for the sync/async bridge used by streaming event routing wrappers."""

from __future__ import annotations

import threading

import pytest

from unique_toolkit.experimental.integrations.openai.streaming.event_routing._async_bridge import (
    run_async_from_sync,
)


async def _thread_id() -> int:
    return threading.get_ident()


class _BridgeBoom(RuntimeError):
    """Sentinel exception raised by helpers in the bridge tests."""


async def _raise_boom() -> int:
    raise _BridgeBoom("boom")


@pytest.mark.ai
def test_AI_run_async_from_sync__returns_result__without_running_loop() -> None:
    """
    Purpose: Verify sync callers can execute an async operation normally.
    Why this matters: The public sync wrappers still need to work in plain
      scripts and worker code where no event loop exists yet.
    Setup summary: Run a tiny coroutine through the bridge and assert its value.
    """
    # Arrange / Act
    result = run_async_from_sync(lambda: _thread_id())

    # Assert
    assert result == threading.get_ident()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_run_async_from_sync__returns_result__with_running_loop() -> None:
    """
    Purpose: Verify sync wrappers do not call ``asyncio.run`` on an active loop.
    Why this matters: Notebook, ASGI, and other async callers already own an
      event loop, which would otherwise raise ``RuntimeError``.
    Setup summary: Call the sync bridge from inside pytest's running event loop
      and assert it completes on a helper thread.
    """
    # Arrange
    current_thread_id = threading.get_ident()

    # Act
    result = run_async_from_sync(lambda: _thread_id())

    # Assert
    assert result != current_thread_id


@pytest.mark.ai
def test_AI_run_async_from_sync__propagates_exception__without_running_loop() -> None:
    """
    Purpose: Ensure async failures surface to sync callers when no loop is active.
    Why this matters: Network errors, auth failures, and other exceptions raised
      inside the coroutine must not be silently swallowed by the bridge.
    Setup summary: Invoke the bridge with a coroutine factory that raises and
      assert the exact exception bubbles up to the caller.
    """
    # Arrange / Act / Assert
    with pytest.raises(_BridgeBoom, match="boom"):
        run_async_from_sync(lambda: _raise_boom())


@pytest.mark.ai
@pytest.mark.asyncio
async def test_AI_run_async_from_sync__propagates_exception__with_running_loop() -> (
    None
):
    """
    Purpose: Ensure exceptions from the helper-thread branch are re-raised.
    Why this matters: In notebook/ASGI environments the bridge runs the coroutine
      on a short-lived thread; without explicit re-raising the caller would get
      ``None`` and silently lose the original failure.
    Setup summary: Call the bridge from within pytest's running event loop using
      a coroutine factory that raises and assert the same exception escapes.
    """
    # Arrange / Act / Assert
    with pytest.raises(_BridgeBoom, match="boom"):
        run_async_from_sync(lambda: _raise_boom())
