import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, TypeVar

from aiolimiter import AsyncLimiter

T = TypeVar("T")


async def limited_coro(
    coro: Coroutine[Any, Any, T],
    limiter: AsyncLimiter,
) -> T:
    """Register task to limiter."""
    async with limiter:
        return await coro


async def execute_multiple_coros(
    coroutines: list[Coroutine[Any, Any, T]],
    task_finished_callback: Callable[
        [T],
        Awaitable[None] | None,
    ] = lambda _: None,
    limiter: AsyncLimiter | None = None,
) -> list[T]:
    """Execute ordered coroutines with or without limiter and callback."""
    if limiter:
        tasks = [
            asyncio.create_task(limited_coro(coro, limiter)) for coro in coroutines
        ]
    else:
        tasks = [asyncio.create_task(coro) for coro in coroutines]

    for completed_task in asyncio.as_completed(tasks):
        result = await completed_task
        callback_res = task_finished_callback(result)
        if asyncio.iscoroutine(callback_res):
            await callback_res

    return await asyncio.gather(*tasks)
