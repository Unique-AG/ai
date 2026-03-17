from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.agentic.evaluation.evaluation_manager import (
    Evaluation,
    EvaluationManager,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricName,
    EvaluationMetricResult,
)


class TestEvaluationManagerExecutionTimes:
    """Test suite for EvaluationManager execution time tracking"""

    @pytest.fixture
    def manager(self):
        mock_logger = MagicMock()
        mock_chat_service = MagicMock()
        return EvaluationManager(logger=mock_logger, chat_service=mock_chat_service)

    @pytest.fixture
    def mock_evaluation(self):
        eval_instance = MagicMock(spec=Evaluation)
        eval_instance.get_name.return_value = EvaluationMetricName.HALLUCINATION
        eval_instance.name = EvaluationMetricName.HALLUCINATION

        async def fake_run(loop_response):
            return EvaluationMetricResult(
                name=EvaluationMetricName.HALLUCINATION,
                is_positive=True,
                value="GREEN",
                reason="No hallucination detected",
            )

        eval_instance.run = AsyncMock(side_effect=fake_run)
        return eval_instance

    @pytest.mark.ai
    def test_execution_times_initialized_empty(self, manager) -> None:
        assert manager._execution_times == {}

    @pytest.mark.ai
    def test_get_execution_times_returns_copy(self, manager) -> None:
        manager._execution_times = {"hallucination": 0.5}
        result = manager.get_execution_times()

        assert result == {"hallucination": 0.5}
        assert result is not manager._execution_times

    @pytest.mark.ai
    def test_get_execution_times_returns_empty_dict_initially(self, manager) -> None:
        result = manager.get_execution_times()
        assert result == {}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_evaluation_call_records_execution_time(
        self, manager, mock_evaluation
    ) -> None:
        manager.add_evaluation(mock_evaluation)
        manager._chat_service.create_message_assessment_async = AsyncMock()

        mock_loop_response = MagicMock()

        await manager.execute_evaluation_call(
            evaluation_name=EvaluationMetricName.HALLUCINATION,
            loop_response=mock_loop_response,
            assistant_message_id="msg_1",
        )

        times = manager.get_execution_times()
        assert str(EvaluationMetricName.HALLUCINATION) in times
        assert isinstance(times[str(EvaluationMetricName.HALLUCINATION)], float)
        assert times[str(EvaluationMetricName.HALLUCINATION)] >= 0

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_evaluation_call_does_not_record_time_for_missing_evaluation(
        self, manager
    ) -> None:
        mock_loop_response = MagicMock()

        result = await manager.execute_evaluation_call(
            evaluation_name=EvaluationMetricName.HALLUCINATION,
            loop_response=mock_loop_response,
            assistant_message_id="msg_1",
        )

        assert manager.get_execution_times() == {}
        assert result.is_positive is True
        assert result.error is not None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_execute_evaluation_call_rounds_time_to_three_decimals(
        self, manager, mock_evaluation
    ) -> None:
        manager.add_evaluation(mock_evaluation)
        manager._chat_service.create_message_assessment_async = AsyncMock()

        mock_loop_response = MagicMock()

        await manager.execute_evaluation_call(
            evaluation_name=EvaluationMetricName.HALLUCINATION,
            loop_response=mock_loop_response,
            assistant_message_id="msg_1",
        )

        times = manager.get_execution_times()
        time_value = times[str(EvaluationMetricName.HALLUCINATION)]
        parts = str(time_value).split(".")
        if len(parts) == 2:
            assert len(parts[1]) <= 3

    @pytest.mark.ai
    def test_get_execution_times_mutation_does_not_affect_internal_state(
        self, manager
    ) -> None:
        manager._execution_times = {"hallucination": 0.5}
        result = manager.get_execution_times()
        result["hallucination"] = 999.0
        result["extra_key"] = 1.0

        assert manager._execution_times == {"hallucination": 0.5}
