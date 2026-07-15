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
from unique_toolkit.language_model.invocation_stats import (
    LanguageModelInvocationStats,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

_MODEL_INFO = "gpt-4-test"


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
        invocation_stats: list[LanguageModelInvocationStats],
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
                invocation_stats=invocation_stats,
            )

        eval_instance.run = AsyncMock(side_effect=fake_run)
        eval_instance.get_assessment_type.return_value = MagicMock()
        return eval_instance

    @pytest.mark.ai
    def test_get_invocation_stats__no_evaluations_run__returns_empty_list(
        self, manager
    ) -> None:
        assert manager.get_invocation_stats() == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_evaluations__single_evaluation__records_invocation_stats(
        self, manager
    ) -> None:
        stats = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source=str(EvaluationMetricName.HALLUCINATION),
        )
        evaluation = self._make_evaluation(EvaluationMetricName.HALLUCINATION, [stats])
        manager.add_evaluation(evaluation)
        mock_loop_response = MagicMock()

        await manager.run_evaluations(
            [EvaluationMetricName.HALLUCINATION], mock_loop_response, "msg_1"
        )

        assert manager.get_invocation_stats() == [
            LanguageModelInvocationStats.from_usage(
                _MODEL_INFO,
                LanguageModelTokenUsage(
                    completion_tokens=10, prompt_tokens=20, total_tokens=30
                ),
                source=str(EvaluationMetricName.HALLUCINATION),
            )
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_evaluations__multiple_evaluations__records_all_invocation_stats(
        self, manager
    ) -> None:
        hallucination_stats = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source=str(EvaluationMetricName.HALLUCINATION),
        )
        relevancy_stats = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=2, total_tokens=3
            ),
            source=str(EvaluationMetricName.CONTEXT_RELEVANCY),
        )
        hallucination = self._make_evaluation(
            EvaluationMetricName.HALLUCINATION, [hallucination_stats]
        )
        relevancy = self._make_evaluation(
            EvaluationMetricName.CONTEXT_RELEVANCY, [relevancy_stats]
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

        recorded = manager.get_invocation_stats()
        assert len(recorded) == 2
        assert recorded[0].source == str(EvaluationMetricName.HALLUCINATION)
        assert recorded[0].token_usage == LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )
        assert recorded[1].source == str(EvaluationMetricName.CONTEXT_RELEVANCY)
        assert recorded[1].token_usage == LanguageModelTokenUsage(
            completion_tokens=1, prompt_tokens=2, total_tokens=3
        )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_evaluations__no_invocation_stats__not_recorded(
        self, manager
    ) -> None:
        """An evaluation that made no LLM call (invocation_stats=[], e.g. a
        deterministic/rule-based check) must not contribute any entries."""
        evaluation = self._make_evaluation(EvaluationMetricName.HALLUCINATION, [])
        manager.add_evaluation(evaluation)
        mock_loop_response = MagicMock()

        await manager.run_evaluations(
            [EvaluationMetricName.HALLUCINATION], mock_loop_response, "msg_1"
        )

        assert manager.get_invocation_stats() == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_evaluations__resets_invocation_stats_between_runs(
        self, manager
    ) -> None:
        stats = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source=str(EvaluationMetricName.HALLUCINATION),
        )
        evaluation = self._make_evaluation(EvaluationMetricName.HALLUCINATION, [stats])
        manager.add_evaluation(evaluation)
        mock_loop_response = MagicMock()

        await manager.run_evaluations(
            [EvaluationMetricName.HALLUCINATION], mock_loop_response, "msg_1"
        )
        assert manager.get_invocation_stats() != []

        await manager.run_evaluations([], mock_loop_response, "msg_1")
        assert manager.get_invocation_stats() == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_run_evaluations__preserves_producer_source(self, manager) -> None:
        """`source` is mandatory on LanguageModelInvocationStats -- the
        manager just collects whatever each evaluation already set, it does
        not stamp or override it."""
        stats = LanguageModelInvocationStats.from_usage(
            _MODEL_INFO,
            LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source="custom_source",
        )
        evaluation = self._make_evaluation(EvaluationMetricName.HALLUCINATION, [stats])
        manager.add_evaluation(evaluation)
        mock_loop_response = MagicMock()

        await manager.run_evaluations(
            [EvaluationMetricName.HALLUCINATION], mock_loop_response, "msg_1"
        )

        recorded = manager.get_invocation_stats()
        assert len(recorded) == 1
        assert recorded[0].source == "custom_source"
