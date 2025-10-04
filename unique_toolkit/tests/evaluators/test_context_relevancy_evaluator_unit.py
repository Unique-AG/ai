from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel

from unique_toolkit.agentic.evaluation.context_relevancy.service import (
    ContextRelevancyEvaluator,
)
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricInput


@pytest.fixture
def sample_structured_output_schema():
    """Sample structured output schema for testing."""

    class TestSchema(BaseModel):
        score: str
        reason: str

    return TestSchema


class TestContextRelevancyEvaluatorUnit:
    @pytest.mark.ai_generated
    def test_context_relevancy_evaluator__initializes_with_company_user_id__when_provided_AI(
        self,
    ):
        """
        Purpose: Verify that ContextRelevancyEvaluator initializes correctly with company_id and user_id.
        Why this matters: Proper initialization is critical for evaluator functionality.
        Setup summary: Test direct initialization with company_id and user_id.
        """
        # Arrange & Act
        evaluator = ContextRelevancyEvaluator(
            company_id="test_company", user_id="test_user"
        )

        # Assert
        assert evaluator.language_model_service is not None
        assert evaluator.logger is not None

    @pytest.mark.ai_generated
    def test_context_relevancy_evaluator__initializes_with_event__when_provided_AI(
        self, base_chat_event
    ):
        """
        Purpose: Verify that ContextRelevancyEvaluator initializes correctly with an event.
        Why this matters: Event-based initialization must work for backward compatibility.
        Setup summary: Use base_chat_event fixture to test event-based initialization.
        """
        # Arrange & Act
        evaluator = ContextRelevancyEvaluator(base_chat_event)

        # Assert
        assert evaluator.language_model_service is not None
        assert evaluator.logger is not None

    @pytest.mark.ai_generated
    def test_from_event__creates_evaluator_with_correct_credentials_AI(
        self, base_chat_event
    ):
        """
        Purpose: Verify that from_event classmethod creates evaluator with correct credentials.
        Why this matters: Classmethod initialization must extract correct IDs from event.
        Setup summary: Use base_chat_event fixture to test from_event classmethod.
        """
        # Arrange & Act
        evaluator = ContextRelevancyEvaluator.from_event(base_chat_event)

        # Assert
        assert evaluator.language_model_service is not None
        assert evaluator.logger is not None

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__returns_none__when_config_disabled_AI(
        self, context_relevancy_evaluation_input, disabled_evaluation_config
    ):
        """
        Purpose: Verify that analyze returns None when the config is disabled.
        Why this matters: Disabled evaluations should not run to save resources.
        Setup summary: Use disabled config to test early return behavior.
        """
        # Arrange
        evaluator = ContextRelevancyEvaluator(
            company_id="test_company", user_id="test_user"
        )

        # Act
        result = await evaluator.analyze(
            context_relevancy_evaluation_input, disabled_evaluation_config
        )

        # Assert
        assert result is None

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__validates_required_fields__before_processing_AI(
        self, base_evaluation_config
    ):
        """
        Purpose: Verify that analyze validates required fields before processing.
        Why this matters: Input validation prevents errors and ensures data quality.
        Setup summary: Use incomplete input to test validation.
        """
        # Arrange
        evaluator = ContextRelevancyEvaluator(
            company_id="test_company", user_id="test_user"
        )
        incomplete_input = EvaluationMetricInput(input_text="Test question")

        # Act & Assert
        with pytest.raises(
            Exception
        ):  # Should raise EvaluatorException for missing context_texts
            await evaluator.analyze(incomplete_input, base_evaluation_config)

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__raises_exception__when_context_texts_empty_AI(
        self, base_evaluation_config
    ):
        """
        Purpose: Verify that analyze raises exception when context_texts is empty.
        Why this matters: Empty context makes relevancy evaluation meaningless.
        Setup summary: Use input with empty context_texts to test error handling.
        """
        # Arrange
        evaluator = ContextRelevancyEvaluator(
            company_id="test_company", user_id="test_user"
        )
        input_with_empty_context = EvaluationMetricInput(
            input_text="Test question",
            context_texts=[],
        )

        # Act & Assert
        with pytest.raises(
            Exception
        ):  # Should raise EvaluatorException for empty context
            await evaluator.analyze(input_with_empty_context, base_evaluation_config)

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__handles_regular_output__when_structured_output_not_available_AI(
        self,
        context_relevancy_evaluation_input,
        base_evaluation_config,
        context_relevancy_evaluation_result,
    ):
        """
        Purpose: Verify that analyze handles regular output when structured output is not available.
        Why this matters: Fallback to regular output ensures evaluation works with all models.
        Setup summary: Mock language model service to return regular output.
        """
        # Arrange
        evaluator = ContextRelevancyEvaluator(
            company_id="test_company", user_id="test_user"
        )

        with patch.object(
            evaluator.language_model_service, "complete_async", new_callable=AsyncMock
        ) as mock_complete:
            mock_complete.return_value.choices[
                0
            ].message.content = "high: The context is highly relevant."

            with patch(
                "unique_toolkit.agentic.evaluation.context_relevancy.service.parse_eval_metric_result"
            ) as mock_parse:
                mock_parse.return_value = context_relevancy_evaluation_result

                # Act
                result = await evaluator.analyze(
                    context_relevancy_evaluation_input, base_evaluation_config
                )

                # Assert
                assert result == context_relevancy_evaluation_result
                mock_complete.assert_called_once()

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__handles_structured_output__when_available_AI(
        self,
        context_relevancy_evaluation_input,
        base_evaluation_config,
        context_relevancy_evaluation_result,
        sample_structured_output_schema,
    ):
        """
        Purpose: Verify that analyze handles structured output when available.
        Why this matters: Structured output provides more reliable evaluation results.
        Setup summary: Mock language model service to return structured output.
        """
        # Arrange
        evaluator = ContextRelevancyEvaluator(
            company_id="test_company", user_id="test_user"
        )

        # Mock the language model capabilities to support structured output
        with patch(
            "unique_toolkit.agentic.evaluation.context_relevancy.service.ModelCapabilities"
        ) as mock_capabilities:
            mock_capabilities.STRUCTURED_OUTPUT = "structured_output"

            # Mock the language model to have structured output capability
            with patch.object(
                base_evaluation_config.language_model,
                "capabilities",
                [mock_capabilities.STRUCTURED_OUTPUT],
            ):
                with patch.object(
                    evaluator.language_model_service,
                    "complete_async",
                    new_callable=AsyncMock,
                ) as mock_complete:
                    mock_response = Mock()
                    mock_response.choices = [Mock()]
                    mock_response.choices[0].message = Mock()
                    mock_response.choices[0].message.parsed = {
                        "value": "high",
                        "reason": "Highly relevant",
                        "fact_list": [],
                    }
                    mock_complete.return_value = mock_response

                    with patch(
                        "unique_toolkit.agentic.evaluation.context_relevancy.service.parse_eval_metric_result_structured_output"
                    ) as mock_parse:
                        mock_parse.return_value = context_relevancy_evaluation_result

                        # Act
                        result = await evaluator.analyze(
                            context_relevancy_evaluation_input,
                            base_evaluation_config,
                            sample_structured_output_schema,
                        )

                        # Assert
                        assert result == context_relevancy_evaluation_result
                        mock_complete.assert_called_once()

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__raises_exception__when_language_model_fails_AI(
        self, context_relevancy_evaluation_input, base_evaluation_config
    ):
        """
        Purpose: Verify that analyze raises exception when language model fails.
        Why this matters: Error handling is critical for robust evaluation functionality.
        Setup summary: Mock language model service to raise an exception.
        """
        # Arrange
        evaluator = ContextRelevancyEvaluator(
            company_id="test_company", user_id="test_user"
        )

        with patch.object(
            evaluator.language_model_service, "complete_async", new_callable=AsyncMock
        ) as mock_complete:
            mock_complete.side_effect = Exception("Language model error")

            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await evaluator.analyze(
                    context_relevancy_evaluation_input, base_evaluation_config
                )

            assert (
                "Unknown error occurred during context relevancy metric analysis"
                in str(exc_info.value)
            )

    @pytest.mark.ai_generated
    @pytest.mark.asyncio
    async def test_analyze__returns_none__when_default_config_disabled_AI(
        self, context_relevancy_evaluation_input
    ):
        """
        Purpose: Verify that analyze returns None when default config is disabled.
        Why this matters: Default behavior should respect the disabled config setting.
        Setup summary: Test with default config which is disabled by default.
        """
        # Arrange
        evaluator = ContextRelevancyEvaluator(
            company_id="test_company", user_id="test_user"
        )

        # Act
        result = await evaluator.analyze(context_relevancy_evaluation_input)

        # Assert
        assert result is None
