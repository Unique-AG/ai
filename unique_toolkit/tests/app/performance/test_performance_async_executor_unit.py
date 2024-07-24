import asyncio
import logging
import unittest
from unittest.mock import MagicMock, patch

from unique_toolkit.app.performance.async_executor import AsyncExecutor


class TestAsyncExecutor(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test_logger")
        self.executor = AsyncExecutor(logger=self.logger)

    async def async_task(self, result):
        await asyncio.sleep(0.1)
        return result

    def test_init(self):
        self.assertIsInstance(self.executor.logger, logging.Logger)
        self.assertIsNotNone(self.executor.context_manager)

    @patch("async_executor.asyncio.Semaphore")
    @patch("async_executor.asyncio.gather")
    async def test_run_async_tasks(self, mock_gather, mock_semaphore):
        mock_gather.return_value = [1, 2, 3]
        mock_semaphore.return_value.__aenter__.return_value = None
        mock_semaphore.return_value.__aexit__.return_value = None

        tasks = [self.async_task(i) for i in range(3)]
        results = await self.executor.run_async_tasks(tasks, max_tasks=2)

        self.assertEqual(results, [1, 2, 3])
        mock_semaphore.assert_called_once_with(2)
        mock_gather.assert_called_once()

    @patch("async_executor.ThreadPoolExecutor")
    async def test_run_async_tasks_in_threads(self, mock_thread_pool):
        mock_executor = MagicMock()
        mock_thread_pool.return_value.__enter__.return_value = mock_executor
        mock_executor.map.return_value = [[1], [2, 3]]

        tasks = [self.async_task(i) for i in range(3)]
        results = await self.executor.run_async_tasks_in_threads(
            tasks, max_threads=2, max_tasks=2
        )

        self.assertEqual(results, [1, 2, 3])
        mock_thread_pool.assert_called_once_with(max_workers=2)
        mock_executor.map.assert_called_once()

    async def test_run_async_tasks_with_exception(self):
        async def failing_task():
            raise ValueError("Test exception")

        tasks = [self.async_task(1), failing_task(), self.async_task(3)]
        results = await self.executor.run_async_tasks(tasks, max_tasks=2)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], 1)
        self.assertIsInstance(results[1], ValueError)
        self.assertEqual(str(results[1]), "Test exception")
        self.assertEqual(results[2], 3)

    @patch("async_executor.asyncio.new_event_loop")
    async def test_run_async_tasks_in_threads_with_exception(self, mock_new_event_loop):
        mock_loop = MagicMock()
        mock_new_event_loop.return_value = mock_loop
        mock_loop.run_until_complete.side_effect = [
            [1],
            Exception("Test thread exception"),
            [3],
        ]

        tasks = [self.async_task(i) for i in range(3)]
        with self.assertRaises(Exception) as context:
            await self.executor.run_async_tasks_in_threads(
                tasks, max_threads=3, max_tasks=1
            )

        self.assertEqual(str(context.exception), "Test thread exception")
