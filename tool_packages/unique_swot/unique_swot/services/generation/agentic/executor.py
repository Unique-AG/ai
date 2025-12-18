import asyncio
from enum import StrEnum
from typing import Any, Awaitable, Callable, Sequence


class ExecutionMode(StrEnum):
    SEQUENTIAL = "Sequential"
    CONCURRENT = "Concurrent"


class AgenticPlanExecutor:
    """
    Register async callables with their arguments and run them sequentially or
    concurrently. Execution captures exceptions instead of raising them so
    callers can inspect failures.
    """

    def __init__(
        self, *, execution_mode: ExecutionMode, max_concurrent_tasks: int | None = None
    ):
        self._execution_mode = execution_mode
        self._max_concurrent_tasks = max_concurrent_tasks or 10
        self._queue: list[
            tuple[Callable[..., Awaitable[Any]], tuple[Any, ...], dict[str, Any]]
        ] = []

    def add(self, fn: Callable[..., Awaitable[Any]], /, *args: Any, **kwargs: Any):
        """Register an awaitable function with its arguments."""
        self._queue.append((fn, args, kwargs))

    async def run(self) -> Sequence[Exception | Any]:
        """Execute all registered tasks and return per-task exceptions (or None)."""
        try:
            match self._execution_mode:
                case ExecutionMode.SEQUENTIAL:
                    return await self._run_sequential()
                case ExecutionMode.CONCURRENT:
                    return await self._run_concurrent()
                case _:
                    raise ValueError(f"Invalid execution mode: {self._execution_mode}")
        finally:
            # Always clear the queue after running to avoid memory leaks
            # and to avoid running the same tasks multiple times
            self._queue.clear()

    async def _run_sequential(self) -> Sequence[Exception | Any]:
        results: list[Exception | None] = []
        for fn, args, kwargs in self._queue:
            try:
                result = await fn(*args, **kwargs)
                results.append(result)
            except Exception as exc:  # noqa: BLE001
                results.append(exc)
        return results

    async def _run_concurrent(self) -> Sequence[Exception | Any]:
        semaphore = asyncio.Semaphore(self._max_concurrent_tasks)

        async def _runner(
            fn: Callable[..., Awaitable[Any]],
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ):
            async with semaphore:
                try:
                    result = await fn(*args, **kwargs)
                    return result
                except Exception as exc:  # noqa: BLE001
                    return exc

        tasks = [
            asyncio.create_task(_runner(fn, args, kwargs))
            for fn, args, kwargs in self._queue
        ]
        return await asyncio.gather(*tasks)
