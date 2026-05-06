from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    Postprocessor,
    PostprocessorManager,
)


class TestPostprocessorManagerExecutionTimes:
    """Test suite for PostprocessorManager execution time tracking"""

    @pytest.fixture
    def manager(self):
        mock_logger = MagicMock()
        mock_chat_service = MagicMock()
        return PostprocessorManager(logger=mock_logger, chat_service=mock_chat_service)

    @pytest.fixture
    def mock_postprocessor(self):
        pp = MagicMock(spec=Postprocessor)
        pp.name = "source_handler"
        pp.run = AsyncMock()
        return pp

    @pytest.mark.ai
    def test_execution_times_initialized_empty(self, manager) -> None:
        assert manager._execution_times == {}

    @pytest.mark.ai
    def test_get_execution_times_returns_copy(self, manager) -> None:
        manager._execution_times = {"source_handler": 0.3}
        result = manager.get_execution_times()

        assert result == {"source_handler": 0.3}
        assert result is not manager._execution_times

    @pytest.mark.ai
    def test_get_execution_times_returns_empty_dict_initially(self, manager) -> None:
        result = manager.get_execution_times()
        assert result == {}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors_records_execution_time(
        self, manager, mock_postprocessor
    ) -> None:
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response,
            postprocessor_instance=mock_postprocessor,
        )

        times = manager.get_execution_times()
        assert "source_handler" in times
        assert isinstance(times["source_handler"], float)
        assert times["source_handler"] >= 0

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors_rounds_time_to_three_decimals(
        self, manager, mock_postprocessor
    ) -> None:
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response,
            postprocessor_instance=mock_postprocessor,
        )

        times = manager.get_execution_times()
        time_value = times["source_handler"]
        parts = str(time_value).split(".")
        if len(parts) == 2:
            assert len(parts[1]) <= 3

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_multiple_postprocessors_records_all_times(
        self, manager
    ) -> None:
        pp1 = MagicMock(spec=Postprocessor)
        pp1.name = "source_handler"
        pp1.run = AsyncMock()

        pp2 = MagicMock(spec=Postprocessor)
        pp2.name = "citation_fixer"
        pp2.run = AsyncMock()

        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response,
            postprocessor_instance=pp1,
        )
        await manager.execute_postprocessors(
            loop_response=mock_loop_response,
            postprocessor_instance=pp2,
        )

        times = manager.get_execution_times()
        assert "source_handler" in times
        assert "citation_fixer" in times

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_same_postprocessor_twice_overwrites_time(
        self, manager, mock_postprocessor
    ) -> None:
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response,
            postprocessor_instance=mock_postprocessor,
        )
        first_time = manager.get_execution_times()["source_handler"]

        await manager.execute_postprocessors(
            loop_response=mock_loop_response,
            postprocessor_instance=mock_postprocessor,
        )
        second_time = manager.get_execution_times()["source_handler"]

        assert isinstance(first_time, float)
        assert isinstance(second_time, float)

    @pytest.mark.ai
    def test_get_execution_times_mutation_does_not_affect_internal_state(
        self, manager
    ) -> None:
        manager._execution_times = {"source_handler": 0.3}
        result = manager.get_execution_times()
        result["source_handler"] = 999.0
        result["extra_key"] = 1.0

        assert manager._execution_times == {"source_handler": 0.3}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors_calls_run(
        self, manager, mock_postprocessor
    ) -> None:
        mock_loop_response = MagicMock()

        await manager.execute_postprocessors(
            loop_response=mock_loop_response,
            postprocessor_instance=mock_postprocessor,
        )

        mock_postprocessor.run.assert_called_once_with(mock_loop_response)
