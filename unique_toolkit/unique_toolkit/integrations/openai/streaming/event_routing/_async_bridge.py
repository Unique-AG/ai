"""Helpers for exposing synchronous wrappers around async streaming event routing."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine
from queue import SimpleQueue
from typing import Literal, TypeVar

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

    outcome: SimpleQueue[
        tuple[Literal["result"], _T] | tuple[Literal["error"], BaseException]
    ] = SimpleQueue()

    def runner() -> None:
        try:
            outcome.put(("result", asyncio.run(coro_factory())))
        except BaseException as exc:
            outcome.put(("error", exc))

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()

    thread_outcome = outcome.get()
    if thread_outcome[0] == "error":
        raise thread_outcome[1]
    return thread_outcome[1]
