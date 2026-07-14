import asyncio
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

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_postprocessors_returns_run_result(
        self, manager, mock_postprocessor
    ) -> None:
        mock_loop_response = MagicMock()
        expected = {"count": 1, "filetypes": ["csv"]}
        mock_postprocessor.run.return_value = expected

        result = await manager.execute_postprocessors(
            loop_response=mock_loop_response,
            postprocessor_instance=mock_postprocessor,
        )

        assert result == expected

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_postprocessors_returns_results_by_name(
        self, manager, mock_postprocessor
    ) -> None:
        expected = {"count": 1, "filetypes": ["csv"]}
        mock_postprocessor.get_name.return_value = "source_handler"
        mock_postprocessor.run.return_value = expected
        mock_postprocessor.apply_postprocessing_to_response.return_value = False
        manager.add_postprocessor(mock_postprocessor)

        outputs = await manager.run_postprocessors(MagicMock())

        assert outputs == {"source_handler": expected}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_side_effect_postprocessor_does_not_delay_message_update(
        self, manager
    ) -> None:
        side_effect_release = asyncio.Event()
        side_effect_finished = asyncio.Event()
        message_updated = asyncio.Event()

        async def run_side_effect(_loop_response) -> None:
            await side_effect_release.wait()
            side_effect_finished.set()

        def apply_message_postprocessing(loop_response) -> bool:
            loop_response.message.text += " follow-up"
            return True

        side_effect_postprocessor = MagicMock(spec=Postprocessor)
        side_effect_postprocessor.name = "user_memory"
        side_effect_postprocessor.affects_assistant_message.return_value = False
        side_effect_postprocessor.run = AsyncMock(side_effect=run_side_effect)

        message_postprocessor = MagicMock(spec=Postprocessor)
        message_postprocessor.name = "follow_up"
        message_postprocessor.affects_assistant_message.return_value = True
        message_postprocessor.run = AsyncMock(return_value=None)
        message_postprocessor.apply_postprocessing_to_response.side_effect = (
            apply_message_postprocessing
        )

        manager.add_postprocessor(side_effect_postprocessor)
        manager.add_postprocessor(message_postprocessor)
        manager._chat_service.modify_assistant_message_async = AsyncMock(
            side_effect=lambda **_kwargs: message_updated.set()
        )

        loop_response = MagicMock()
        loop_response.message.text = "answer"
        loop_response.message.id = "assistant-message"
        loop_response.message.references = []
        run_task = asyncio.create_task(manager.run_postprocessors(loop_response))

        await asyncio.wait_for(message_updated.wait(), timeout=1)

        assert not side_effect_finished.is_set()
        assert not run_task.done()
        manager._chat_service.modify_assistant_message_async.assert_awaited_once_with(
            content="answer follow-up",
            message_id="assistant-message",
            references=[],
        )

        side_effect_release.set()
        await run_task

        assert side_effect_finished.is_set()
        manager._chat_service.modify_assistant_message_async.assert_awaited_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_message_postprocessors_publish_one_deterministic_update(
        self, manager
    ) -> None:
        first_release = asyncio.Event()
        second_finished = asyncio.Event()

        async def run_first(_loop_response) -> None:
            await first_release.wait()

        async def run_second(_loop_response) -> None:
            second_finished.set()

        def apply_first(loop_response) -> bool:
            loop_response.message.text += " first"
            return True

        def apply_second(loop_response) -> bool:
            loop_response.message.text += " second"
            return True

        first_postprocessor = MagicMock(spec=Postprocessor)
        first_postprocessor.name = "first"
        first_postprocessor.affects_assistant_message.return_value = True
        first_postprocessor.run = AsyncMock(side_effect=run_first)
        first_postprocessor.apply_postprocessing_to_response.side_effect = apply_first

        second_postprocessor = MagicMock(spec=Postprocessor)
        second_postprocessor.name = "second"
        second_postprocessor.affects_assistant_message.return_value = True
        second_postprocessor.run = AsyncMock(side_effect=run_second)
        second_postprocessor.apply_postprocessing_to_response.side_effect = apply_second

        manager.add_postprocessor(first_postprocessor)
        manager.add_postprocessor(second_postprocessor)
        manager._chat_service.modify_assistant_message_async = AsyncMock()

        loop_response = MagicMock()
        loop_response.message.text = "answer"
        loop_response.message.id = "assistant-message"
        loop_response.message.references = []
        run_task = asyncio.create_task(manager.run_postprocessors(loop_response))

        await asyncio.wait_for(second_finished.wait(), timeout=1)

        manager._chat_service.modify_assistant_message_async.assert_not_awaited()

        first_release.set()
        await run_task

        manager._chat_service.modify_assistant_message_async.assert_awaited_once_with(
            content="answer first second",
            message_id="assistant-message",
            references=[],
        )
