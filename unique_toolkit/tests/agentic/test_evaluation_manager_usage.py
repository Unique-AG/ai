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
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage


class TestEvaluationManagerUsage:
    """Test suite for EvaluationManager token-usage tracking.

    Mirrors test_evaluation_manager_execution_times.py — evaluations like
    HallucinationEvaluation make their own LLM call outside the main
    answer-generating call, and that usage was previously silently dropped.
    """

    @pytest.fixture
    def manager(self):
        mock_logger = MagicMock()
        mock_chat_service = MagicMock()
        manager = EvaluationManager(logger=mock_logger, chat_service=mock_chat_service)
        manager._chat_service.create_message_assessment_async = AsyncMock()
        manager._chat_service.modify_message_assessment_async = AsyncMock()
        return manager

    def _make_evaluation(
        self,
        name: EvaluationMetricName,
        usage: LanguageModelTokenUsage | None,
    ) -> MagicMock:
        eval_instance = MagicMock(spec=Evaluation)
        eval_instance.get_name.return_value = name
        eval_instance.name = name

        async def fake_run(loop_response):
            return EvaluationMetricResult(
                name=name,
                is_positive=True,
                value="GREEN",
                reason="ok",
                usage=usage,
            )

        eval_instance.run = AsyncMock(side_effect=fake_run)
        eval_instance.get_assessment_type.return_value = MagicMock()
        return eval_instance

    @pytest.mark.ai
    def test_get_usage__no_evaluations_run__returns_none(self, manager) -> None:
        assert manager.get_usage() is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_evaluations__single_evaluation__records_usage(
        self, manager
    ) -> None:
        evaluation = self._make_evaluation(
            EvaluationMetricName.HALLUCINATION,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
        )
        manager.add_evaluation(evaluation)
        mock_loop_response = MagicMock()

        await manager.run_evaluations(
            [EvaluationMetricName.HALLUCINATION], mock_loop_response, "msg_1"
        )

        assert manager.get_usage() == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_evaluations__multiple_evaluations__sums_usage(
        self, manager
    ) -> None:
        hallucination = self._make_evaluation(
            EvaluationMetricName.HALLUCINATION,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
        )
        relevancy = self._make_evaluation(
            EvaluationMetricName.CONTEXT_RELEVANCY,
            LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=2, total_tokens=3
            ),
        )
        manager.add_evaluation(hallucination)
        manager.add_evaluation(relevancy)
        mock_loop_response = MagicMock()

        await manager.run_evaluations(
            [
                EvaluationMetricName.HALLUCINATION,
                EvaluationMetricName.CONTEXT_RELEVANCY,
            ],
            mock_loop_response,
            "msg_1",
        )

        assert manager.get_usage() == LanguageModelTokenUsage(
            completion_tokens=11, prompt_tokens=22, total_tokens=33
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_evaluations__usage_none__not_recorded(self, manager) -> None:
        """An evaluation that made no LLM call (usage=None, e.g. a
        deterministic/rule-based check) must not contribute a zeroed entry."""
        evaluation = self._make_evaluation(EvaluationMetricName.HALLUCINATION, None)
        manager.add_evaluation(evaluation)
        mock_loop_response = MagicMock()

        await manager.run_evaluations(
            [EvaluationMetricName.HALLUCINATION], mock_loop_response, "msg_1"
        )

        assert manager.get_usage() is None

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_evaluations__resets_usage_between_runs(self, manager) -> None:
        evaluation = self._make_evaluation(
            EvaluationMetricName.HALLUCINATION,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
        )
        manager.add_evaluation(evaluation)
        mock_loop_response = MagicMock()

        await manager.run_evaluations(
            [EvaluationMetricName.HALLUCINATION], mock_loop_response, "msg_1"
        )
        assert manager.get_usage() is not None

        await manager.run_evaluations([], mock_loop_response, "msg_1")
        assert manager.get_usage() is None
