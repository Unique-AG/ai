import asyncio
import logging
from unittest.mock import Mock

import pytest

from unique_toolkit.app.performance.async_tasks import run_async_tasks_parallel


class TestRunAsyncTasksParallel:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)

    @pytest.mark.asyncio
    async def test_successful_tasks(self):
        async def successful_task(result):
            await asyncio.sleep(0.1)
            return result

        tasks = [successful_task(i) for i in range(5)]
        results = await run_async_tasks_parallel(tasks, max_tasks=2, logger=self.logger)

        assert len(results) == 5
        assert results == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_failed_tasks(self):
        async def failed_task():
            await asyncio.sleep(0.1)
            raise ValueError("Task failed")

        tasks = [failed_task() for _ in range(3)]
        results = await run_async_tasks_parallel(tasks, logger=self.logger)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, ValueError)
            assert str(result) == "Task failed"

    @pytest.mark.asyncio
    async def test_mixed_tasks(self):
        async def successful_task(result):
            await asyncio.sleep(0.1)
            return result

        async def failed_task():
            await asyncio.sleep(0.1)
            raise ValueError("Task failed")

        tasks = [successful_task(1), failed_task(), successful_task(2)]
        results = await run_async_tasks_parallel(tasks, logger=self.logger)

        assert len(results) == 3
        assert results[0] == 1
        assert isinstance(results[1], ValueError)
        assert results[2] == 2

    @pytest.mark.asyncio
    async def test_max_tasks(self):
        async def slow_task(result):
            await asyncio.sleep(0.5)
            return result

        tasks = [slow_task(i) for i in range(5)]

        start_time = asyncio.get_event_loop().time()
        results = await run_async_tasks_parallel(tasks, max_tasks=2, logger=self.logger)
        end_time = asyncio.get_event_loop().time()

        assert results == [0, 1, 2, 3, 4]
        # With max_tasks=2, it should take about 1.5 seconds (3 batches of 0.5 seconds)
        assert 1.4 < (end_time - start_time) < 1.6

    @pytest.mark.asyncio
    async def test_logging(self):
        mock_logger = Mock(spec=logging.Logger)

        async def successful_task():
            return "Success"

        async def failed_task():
            raise ValueError("Task failed")

        tasks = [successful_task(), failed_task()]
        await run_async_tasks_parallel(tasks, logger=mock_logger)

        assert mock_logger.info.call_count == 2  # Two tasks started
        assert mock_logger.error.call_count == 1  # One task failed
        assert mock_logger.debug.call_count == 2  # Two tasks finished
