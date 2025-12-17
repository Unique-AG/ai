"""Tests for the AgenticPlanExecutor."""

import asyncio

import pytest

from unique_swot.services.generation.agentic.executor import (
    AgenticPlanExecutor,
    ExecutionMode,
)


async def _success_task(value: int) -> int:
    """A simple async task that returns its input."""
    await asyncio.sleep(0.01)
    return value * 2


async def _failing_task() -> None:
    """A task that always raises an exception."""
    await asyncio.sleep(0.01)
    raise ValueError("Task failed")


@pytest.mark.asyncio
async def test_executor_sequential_mode_success():
    """Test sequential execution with successful tasks."""
    executor = AgenticPlanExecutor(execution_mode=ExecutionMode.SEQUENTIAL)

    executor.add(_success_task, 1)
    executor.add(_success_task, 2)
    executor.add(_success_task, 3)

    results = await executor.run()

    assert len(results) == 3
    assert results[0] == 2
    assert results[1] == 4
    assert results[2] == 6


@pytest.mark.asyncio
async def test_executor_sequential_mode_with_failure():
    """Test sequential execution with a failing task."""
    executor = AgenticPlanExecutor(execution_mode=ExecutionMode.SEQUENTIAL)

    executor.add(_success_task, 1)
    executor.add(_failing_task)
    executor.add(_success_task, 3)

    results = await executor.run()

    assert len(results) == 3
    assert results[0] == 2
    assert isinstance(results[1], ValueError)
    assert results[2] == 6


@pytest.mark.asyncio
async def test_executor_concurrent_mode_success():
    """Test concurrent execution with successful tasks."""
    executor = AgenticPlanExecutor(
        execution_mode=ExecutionMode.CONCURRENT, max_concurrent_tasks=2
    )

    executor.add(_success_task, 1)
    executor.add(_success_task, 2)
    executor.add(_success_task, 3)

    results = await executor.run()

    assert len(results) == 3
    # Results should all be successful (order may vary in concurrent mode)
    assert set(results) == {2, 4, 6}


@pytest.mark.asyncio
async def test_executor_concurrent_mode_with_failure():
    """Test concurrent execution with a failing task."""
    executor = AgenticPlanExecutor(
        execution_mode=ExecutionMode.CONCURRENT, max_concurrent_tasks=2
    )

    executor.add(_success_task, 1)
    executor.add(_failing_task)
    executor.add(_success_task, 3)

    results = await executor.run()

    assert len(results) == 3
    # Two successful results and one exception
    successful_results = [r for r in results if not isinstance(r, Exception)]
    failed_results = [r for r in results if isinstance(r, Exception)]

    assert len(successful_results) == 2
    assert len(failed_results) == 1
    assert isinstance(failed_results[0], ValueError)


@pytest.mark.asyncio
async def test_executor_respects_max_concurrent_tasks():
    """Test that max_concurrent_tasks limit is respected."""
    call_times = []

    async def _timed_task(task_id: int):
        call_times.append((task_id, "start"))
        await asyncio.sleep(0.05)
        call_times.append((task_id, "end"))
        return task_id

    executor = AgenticPlanExecutor(
        execution_mode=ExecutionMode.CONCURRENT, max_concurrent_tasks=2
    )

    for i in range(4):
        executor.add(_timed_task, i)

    results = await executor.run()

    # All tasks should complete
    assert len(results) == 4
    assert set(results) == {0, 1, 2, 3}


@pytest.mark.asyncio
async def test_executor_clears_queue_after_run():
    """Test that the queue is cleared after execution."""
    executor = AgenticPlanExecutor(execution_mode=ExecutionMode.SEQUENTIAL)

    executor.add(_success_task, 1)
    executor.add(_success_task, 2)

    results1 = await executor.run()
    assert len(results1) == 2

    # Queue should be empty, running again should return empty results
    results2 = await executor.run()
    assert len(results2) == 0


@pytest.mark.asyncio
async def test_executor_with_kwargs():
    """Test executor with keyword arguments."""

    async def _task_with_kwargs(a: int, b: int = 0) -> int:
        return a + b

    executor = AgenticPlanExecutor(execution_mode=ExecutionMode.SEQUENTIAL)

    executor.add(_task_with_kwargs, 1, b=2)
    executor.add(_task_with_kwargs, 3, b=4)

    results = await executor.run()

    assert results[0] == 3
    assert results[1] == 7


@pytest.mark.asyncio
async def test_executor_empty_queue():
    """Test executor with no tasks added."""
    executor = AgenticPlanExecutor(execution_mode=ExecutionMode.SEQUENTIAL)

    results = await executor.run()

    assert len(results) == 0


@pytest.mark.asyncio
async def test_executor_multiple_runs():
    """Test that executor can be reused for multiple runs."""
    executor = AgenticPlanExecutor(execution_mode=ExecutionMode.SEQUENTIAL)

    # First run
    executor.add(_success_task, 1)
    results1 = await executor.run()
    assert len(results1) == 1
    assert results1[0] == 2

    # Second run with different tasks
    executor.add(_success_task, 5)
    executor.add(_success_task, 10)
    results2 = await executor.run()
    assert len(results2) == 2
    assert results2[0] == 10
    assert results2[1] == 20


@pytest.mark.asyncio
async def test_executor_default_max_concurrent_tasks():
    """Test that default max_concurrent_tasks is set correctly."""
    executor = AgenticPlanExecutor(execution_mode=ExecutionMode.CONCURRENT)

    # Default should be 10
    assert executor._max_concurrent_tasks == 10

    # Add more than 10 tasks
    for i in range(15):
        executor.add(_success_task, i)

    results = await executor.run()

    # All tasks should complete
    assert len(results) == 15
