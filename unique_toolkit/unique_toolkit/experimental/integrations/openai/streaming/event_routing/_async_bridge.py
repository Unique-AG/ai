"""Helpers for exposing synchronous wrappers around async streaming event routing."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine
from typing import TypeVar, cast

_T = TypeVar("_T")


def run_async_from_sync(
    coro_factory: Callable[[], Coroutine[object, object, _T]],
) -> _T:
    """Run an async operation from a synchronous API.

    ``asyncio.run`` cannot be called when the current thread already owns a
    running event loop. In that case, run the coroutine in a short-lived thread
    with its own event loop so sync callers keep working in notebooks, ASGI
    event handlers, and other loop-driven environments.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())

    result: _T | None = None
    error: BaseException | None = None

    def runner() -> None:
        nonlocal error, result
        try:
            result = asyncio.run(coro_factory())
        except BaseException as exc:
            error = exc

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()

    if error is not None:
        raise error

    return cast(_T, result)
