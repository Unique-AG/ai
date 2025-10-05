from unittest.mock import AsyncMock, Mock

import pytest

from unique_toolkit.agentic.evaluation.evaluation_manager import (
    Evaluation,
    EvaluationManager,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationAssessmentMessage,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.chat.schemas import (
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
)
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse


class MockEvaluation(Evaluation):
    """Mock evaluation for testing purposes."""

    def __init__(self, name: EvaluationMetricName, should_fail: bool = False):
        super().__init__(name)
        self.should_fail = should_fail
        self.run_called = False
        self.assessment_called = False

    def get_assessment_type(self) -> ChatMessageAssessmentType:
        return ChatMessageAssessmentType.HALLUCINATION

    async def run(
        self, loop_response: LanguageModelStreamResponse
    ) -> EvaluationMetricResult:
        self.run_called = True
        if self.should_fail:
            raise Exception("Mock evaluation failed")

        return EvaluationMetricResult(
            name=self.name,
            value="test_value",
            reason="Test reason",
            is_positive=True,
        )

    async def evaluation_metric_to_assessment(
        self, evaluation_result: EvaluationMetricResult
    ) -> EvaluationAssessmentMessage:
        self.assessment_called = True
        return EvaluationAssessmentMessage(
            status=ChatMessageAssessmentStatus.DONE,
            explanation="Test explanation",
            title="Test Title",
            label=ChatMessageAssessmentLabel.GREEN,
            type=ChatMessageAssessmentType.HALLUCINATION,
        )


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock()


@pytest.fixture
def mock_chat_service():
    """Mock chat service for testing."""
    mock_service = Mock()
    mock_service.create_message_assessment_async = AsyncMock()
    mock_service.modify_message_assessment_async = AsyncMock()
    mock_service.update_assessment = Mock()
    return mock_service


@pytest.fixture
def mock_loop_response():
    """Mock language model stream response for testing."""
    return Mock(spec=LanguageModelStreamResponse)


@pytest.fixture
def sample_evaluation_result():
    """Sample evaluation result for testing."""
    return EvaluationMetricResult(
        name=EvaluationMetricName.HALLUCINATION,
        value="low",
        reason="No hallucination detected",
        is_positive=True,
    )


@pytest.fixture
def sample_assessment_message():
    """Sample assessment message for testing."""
    return EvaluationAssessmentMessage(
        status=ChatMessageAssessmentStatus.DONE,
        explanation="No hallucination detected in the response",
        title="Hallucination Check",
        label=ChatMessageAssessmentLabel.GREEN,
        type=ChatMessageAssessmentType.HALLUCINATION,
    )


class TestEvaluationManagerUnit:
    @pytest.mark.ai_generated
    def test_evaluation_manager__initializes_correctly__when_created_AI(
        self, mock_logger, mock_chat_service
    ):
        """
        Purpose: Verify that EvaluationManager initializes correctly with logger and chat service.
        Why this matters: Proper initialization is critical for evaluation management functionality.
        Setup summary: Use mock logger and chat service to test initialization.
        """
        # Arrange & Act
        manager = EvaluationManager(mock_logger, mock_chat_service)

        # Assert
        assert manager._logger == mock_logger
        assert manager._chat_service == mock_chat_service
        assert manager._evaluations == {}
        assert manager._evaluation_passed is True

    @pytest.mark.ai_generated
    def test_add_evaluation__stores_evaluation_by_name__when_added_AI(
        self, mock_logger, mock_chat_service
    ):
        """
        Purpose: Verify that add_evaluation stores evaluation by its name.
        Why this matters: Evaluations must be retrievable by name for execution.
        Setup summary: Create mock evaluation and test storage.
        """
        # Arrange
        manager = EvaluationManager(mock_logger, mock_chat_service)
        evaluation = MockEvaluation(EvaluationMetricName.HALLUCINATION)

        # Act
        manager.add_evaluation(evaluation)

        # Assert
        assert manager._evaluations[EvaluationMetricName.HALLUCINATION] == evaluation

    @pytest.mark.ai_generated
    def test_get_evaluation_by_name__returns_evaluation__when_exists_AI(
        self, mock_logger, mock_chat_service
    ):
        """
        Purpose: Verify that get_evaluation_by_name returns the correct evaluation.
        Why this matters: Evaluation retrieval is essential for execution.
        Setup summary: Add evaluation and test retrieval.
        """
        # Arrange
        manager = EvaluationManager(mock_logger, mock_chat_service)
        evaluation = MockEvaluation(EvaluationMetricName.HALLUCINATION)
        manager.add_evaluation(evaluation)

        # Act
        result = manager.get_evaluation_by_name(EvaluationMetricName.HALLUCINATION)

        # Assert
        assert result == evaluation

    @pytest.mark.ai_generated
    def test_get_evaluation_by_name__returns_none__when_not_exists_AI(
        self, mock_logger, mock_chat_service
    ):
        """
        Purpose: Verify that get_evaluation_by_name returns None when evaluation doesn't exist.
        Why this matters: Graceful handling of missing evaluations is important.
        Setup summary: Test retrieval of non-existent evaluation.
        """
        # Arrange
        manager = EvaluationManager(mock_logger, mock_chat_service)

        # Act
        result = manager.get_evaluation_by_name(EvaluationMetricName.HALLUCINATION)

        # Assert
        assert result is None

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_run_evaluations__executes_all_evaluations__when_successful_AI(
        self,
        mock_logger,
        mock_chat_service,
        mock_loop_response,
        sample_evaluation_result,
        sample_assessment_message,
    ):
        """
        Purpose: Verify that run_evaluations executes all selected evaluations successfully.
        Why this matters: Core functionality must work for evaluation execution.
        Setup summary: Add evaluations and test execution.
        """
        # Arrange
        manager = EvaluationManager(mock_logger, mock_chat_service)
        evaluation1 = MockEvaluation(EvaluationMetricName.HALLUCINATION)
        evaluation2 = MockEvaluation(EvaluationMetricName.CONTEXT_RELEVANCY)
        manager.add_evaluation(evaluation1)
        manager.add_evaluation(evaluation2)

        # Act
        results = await manager.run_evaluations(
            [
                EvaluationMetricName.HALLUCINATION,
                EvaluationMetricName.CONTEXT_RELEVANCY,
            ],
            mock_loop_response,
            "assistant_message_id",
        )

        # Assert
        assert len(results) == 2
        assert evaluation1.run_called
        assert evaluation2.run_called

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_run_evaluations__handles_missing_evaluations__gracefully_AI(
        self, mock_logger, mock_chat_service, mock_loop_response
    ):
        """
        Purpose: Verify that run_evaluations handles missing evaluations gracefully.
        Why this matters: Robust error handling prevents system failures.
        Setup summary: Test execution with non-existent evaluation names.
        """
        # Arrange
        manager = EvaluationManager(mock_logger, mock_chat_service)

        # Act
        results = await manager.run_evaluations(
            [EvaluationMetricName.HALLUCINATION],
            mock_loop_response,
            "assistant_message_id",
        )

        # Assert
        # The implementation returns error results for missing evaluations
        assert len(results) == 1
        assert results[0].name == EvaluationMetricName.HALLUCINATION
        assert "not found" in results[0].reason

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_run_evaluations__handles_evaluation_failures__gracefully_AI(
        self, mock_logger, mock_chat_service, mock_loop_response
    ):
        """
        Purpose: Verify that run_evaluations handles evaluation failures gracefully.
        Why this matters: Individual evaluation failures should not stop other evaluations.
        Setup summary: Add failing evaluation and test error handling.
        """
        # Arrange
        manager = EvaluationManager(mock_logger, mock_chat_service)
        failing_evaluation = MockEvaluation(
            EvaluationMetricName.HALLUCINATION, should_fail=True
        )
        working_evaluation = MockEvaluation(EvaluationMetricName.CONTEXT_RELEVANCY)
        manager.add_evaluation(failing_evaluation)
        manager.add_evaluation(working_evaluation)

        # Act
        results = await manager.run_evaluations(
            [
                EvaluationMetricName.HALLUCINATION,
                EvaluationMetricName.CONTEXT_RELEVANCY,
            ],
            mock_loop_response,
            "assistant_message_id",
        )

        # Assert
        # Should have results from both evaluations (including error results)
        assert len(results) == 2
        assert working_evaluation.run_called
        assert failing_evaluation.run_called  # Should still be called, but fail

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_run_evaluations__calls_assessment_conversion__for_successful_results_AI(
        self, mock_logger, mock_chat_service, mock_loop_response
    ):
        """
        Purpose: Verify that run_evaluations calls assessment conversion for successful results.
        Why this matters: Assessment conversion is needed for user-facing results.
        Setup summary: Add evaluation and verify assessment conversion is called.
        """
        # Arrange
        manager = EvaluationManager(mock_logger, mock_chat_service)
        evaluation = MockEvaluation(EvaluationMetricName.HALLUCINATION)
        manager.add_evaluation(evaluation)

        # Act
        await manager.run_evaluations(
            [EvaluationMetricName.HALLUCINATION],
            mock_loop_response,
            "assistant_message_id",
        )

        # Assert
        assert evaluation.run_called
        assert evaluation.assessment_called

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_run_evaluations__updates_chat_service__with_assessments_AI(
        self, mock_logger, mock_chat_service, mock_loop_response
    ):
        """
        Purpose: Verify that run_evaluations updates chat service with assessment messages.
        Why this matters: Chat integration is essential for user feedback.
        Setup summary: Mock chat service and verify update calls.
        """
        # Arrange
        manager = EvaluationManager(mock_logger, mock_chat_service)
        evaluation = MockEvaluation(EvaluationMetricName.HALLUCINATION)
        manager.add_evaluation(evaluation)

        # Act
        await manager.run_evaluations(
            [EvaluationMetricName.HALLUCINATION],
            mock_loop_response,
            "assistant_message_id",
        )

        # Assert
        # Verify that chat service was called to create/modify assessments
        mock_chat_service.create_message_assessment_async.assert_called()

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_run_evaluations__handles_empty_evaluation_list__gracefully_AI(
        self, mock_logger, mock_chat_service, mock_loop_response
    ):
        """
        Purpose: Verify that run_evaluations handles empty evaluation list gracefully.
        Why this matters: Edge case handling ensures robust functionality.
        Setup summary: Test execution with empty evaluation list.
        """
        # Arrange
        manager = EvaluationManager(mock_logger, mock_chat_service)

        # Act
        results = await manager.run_evaluations(
            [], mock_loop_response, "assistant_message_id"
        )

        # Assert
        assert len(results) == 0
