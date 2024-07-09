import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from typing import Awaitable, Sequence, TypeVar, Union

from quart import Quart

T = TypeVar("T")
Result = Union[T, BaseException]

class AsyncExecutor:
    def __init__(self, app_instance: Quart) -> None:
        self.app = app_instance

    async def run_async_tasks(
        self,
        tasks: Sequence[Awaitable[T]],
        max_tasks: int,
    ) -> list[Result]:
        """
        Executes the given async tasks within one thread non-blocking and returns the results.

        Args:
        tasks (list[Awaitable[T]]): list of async callables to execute in parallel.
        max_tasks (int): Maximum number of tasks for the asyncio Semaphore.

        Returns:
        list[Result]: list of results from the executed tasks.
        """

        async def logging_wrapper(task: Awaitable[T], task_id: int) -> Result:
            thread = threading.current_thread()
            start_time = time.time()

            self.app.logger.info(f"Thread {thread.name} (ID: {thread.ident}) starting task {task_id}")

            try:
                async with self.app.app_context():
                    result = await task
                return result
            except Exception as e:
                self.app.logger.error(f"Thread {thread.name} (ID: {thread.ident}) - Task {task_id} failed with error: {e}")
                return e
            finally:
                end_time = time.time()
                duration = end_time - start_time
                self.app.logger.debug(
                    f"Thread {thread.name} (ID: {thread.ident}) - Task {task_id} finished in {duration:.2f} seconds"
                )

        sem = asyncio.Semaphore(max_tasks)

        async def sem_task(task: Awaitable[T], task_id: int) -> Result:
            async with sem:
                return await logging_wrapper(task, task_id)

        wrapped_tasks: list[Awaitable[Result]] = [sem_task(task, i) for i, task in enumerate(tasks)]

        results: list[Result] = await asyncio.gather(*wrapped_tasks, return_exceptions=True)

        return results
    
    async def run_async_tasks_in_threads(
        self,
        tasks: Sequence[Awaitable[T]],
        max_threads: int,
        max_tasks: int,
    ) -> list[Result[T]]:
        """
        Executes the given async tasks in parallel threads and returns the results.

        Args:
        tasks (list[Awaitable[T]]): list of async callables to execute in parallel.
        max_threads (int): Maximum number of threads.
        max_tasks (int): Maximum number of tasks per thread run in parallel.

        Returns:
        list[Result]: list of results from the executed tasks.
        """
        async def run_in_thread(task_chunk: list[Awaitable[T]]) -> list[Result]:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async with self.app.app_context():
                return await self.run_async_tasks(task_chunk, max_tasks)

        def thread_worker(task_chunk: list[Awaitable[T]], chunk_id: int) -> list[Result]:
            thread = threading.current_thread()
            self.app.logger.info(f"Thread {thread.name} (ID: {thread.ident}) starting chunk {chunk_id} with {len(task_chunk)} tasks")
            
            start_time = time.time()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                results = loop.run_until_complete(run_in_thread(task_chunk))
                end_time = time.time()
                duration = end_time - start_time
                self.app.logger.info(f"Thread {thread.name} (ID: {thread.ident}) finished chunk {chunk_id} in {duration:.2f} seconds")
                return results
            except Exception as e:
                self.app.logger.error(f"Thread {thread.name} (ID: {thread.ident}) encountered an error in chunk {chunk_id}: {str(e)}")
                raise
            finally:
                loop.close()
        
        start_time = time.time()
        # Calculate the number of tasks per thread
        tasks_per_thread: int = ceil(len(tasks) / max_threads)

        # Split tasks into chunks
        task_chunks: list[Sequence[Awaitable[T]]] = [tasks[i:i + tasks_per_thread] for i in range(0, len(tasks), tasks_per_thread)]

        self.app.logger.info(f"Splitting {len(tasks)} tasks into {len(task_chunks)} chunks across {max_threads} threads")

        # Use ThreadPoolExecutor to manage threads
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Submit each chunk of tasks to a thread
            future_results: list[list[Result]] = list(executor.map(
                thread_worker, 
                task_chunks,
                range(len(task_chunks))  # chunk_id
            ))

        # Flatten the results from all threads
        results: list[Result] = [item for sublist in future_results for item in sublist]
        end_time = time.time()
        duration = end_time - start_time
        self.app.logger.info(f"All threads completed. Total results: {len(results)}. Duration: {duration:.2f} seconds")

        return results
    