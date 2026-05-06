import asyncio
import logging
import threading
import time
from typing import (
    Awaitable,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

T = TypeVar("T")
Result = Union[T, BaseException]


async def run_async_tasks_parallel(
    tasks: Sequence[Awaitable[T]],
    max_tasks: Optional[int] = None,
    logger: logging.Logger = logging.getLogger(__name__),
) -> list[Result[T]]:
    """
    Executes the a set of given async tasks and returns the results.

    Args:
    tasks (list[Awaitable[T]]): list of async callables to execute in parallel.
    max_tasks (int): Maximum number of tasks for the asyncio Semaphore.

    Returns:
    list[Result]: list of results from the executed tasks.
    """

    max_tasks = max_tasks or len(tasks)

    async def logging_wrapper(task: Awaitable[T], task_id: int) -> Result[T]:
        thread = threading.current_thread()
        start_time = time.time()

        logger.info(
            f"Thread {thread.name} (ID: {thread.ident}) starting task {task_id}"
        )

        try:
            result = await task
            return result
        except Exception as e:
            logger.error(
                f"Thread {thread.name} (ID: {thread.ident}) - Task {task_id} failed with error: {e}"
            )
            return e
        finally:
            end_time = time.time()
            duration = end_time - start_time
            logger.debug(
                f"Thread {thread.name} (ID: {thread.ident}) - Task {task_id} finished in {duration:.2f} seconds"
            )

    sem = asyncio.Semaphore(max_tasks)

    async def sem_task(task: Awaitable[T], task_id: int) -> Result[T]:
        async with sem:
            return await logging_wrapper(task, task_id)

    wrapped_tasks: list[Awaitable[Result[T]]] = [
        sem_task(task, i) for i, task in enumerate(tasks)
    ]

    results: list[Result[T]] = await asyncio.gather(
        *wrapped_tasks, return_exceptions=True
    )

    return results
