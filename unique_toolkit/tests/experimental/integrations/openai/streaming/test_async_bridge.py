"""Tests for the sync/async bridge used by streaming event routing wrappers."""

from __future__ import annotations

import threading

import pytest

from unique_toolkit.experimental.integrations.openai.streaming.event_routing._async_bridge import (
    run_async_from_sync,
)


async def _thread_id() -> int:
    return threading.get_ident()


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
