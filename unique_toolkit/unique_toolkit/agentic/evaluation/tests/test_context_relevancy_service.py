"""Tests for context relevancy evaluation service."""

from unittest.mock import MagicMock, patch

import pytest

from unique_toolkit.agentic.evaluation.config import EvaluationMetricConfig
from unique_toolkit.agentic.evaluation.context_relevancy.schema import (
    EvaluationSchemaStructuredOutput,
)
from unique_toolkit.agentic.evaluation.exception import EvaluatorException
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricInput,
    EvaluationMetricResult,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelCompletionChoice,
)
from unique_toolkit.language_model.service import LanguageModelResponse


@pytest.mark.ai
@pytest.mark.asyncio
async def test_analyze__returns_none__when_disabled(
    context_relevancy_evaluator: MagicMock,
    sample_evaluation_input: EvaluationMetricInput,
    basic_evaluation_config: EvaluationMetricConfig,
) -> None:
    """
    Purpose: Verify that analyze returns None when evaluation is disabled in config.
    Why this matters: Ensures evaluation can be toggled off without errors or side effects.
    Setup summary: Set config.enabled=False, call analyze, assert None returned.
    """
    # Arrange
    basic_evaluation_config.enabled = False

    # Act
    result = await context_relevancy_evaluator.analyze(
        sample_evaluation_input, basic_evaluation_config
    )

    # Assert
    assert result is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_analyze__raises_evaluator_exception__with_empty_context(
    context_relevancy_evaluator: MagicMock,
    basic_evaluation_config: EvaluationMetricConfig,
) -> None:
    """
    Purpose: Verify that analyze raises exception when context texts are empty.
    Why this matters: Context relevancy evaluation requires at least one context.
    Setup summary: Create input with empty context_texts, assert EvaluatorException raised.
    """
    # Arrange
    input_with_empty_context: EvaluationMetricInput = EvaluationMetricInput(
        input_text="test query", context_texts=[]
    )

    # Act & Assert
    with pytest.raises(EvaluatorException) as exc_info:
        await context_relevancy_evaluator.analyze(
            input_with_empty_context, basic_evaluation_config
        )

    assert "No context texts provided." in str(exc_info.value)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_analyze__returns_valid_result__with_regular_output(
    context_relevancy_evaluator: MagicMock,
    sample_evaluation_input: EvaluationMetricInput,
    basic_evaluation_config: EvaluationMetricConfig,
) -> None:
    """
    Purpose: Verify analyze successfully processes regular (non-structured) output from LLM.
    Why this matters: Core functionality for evaluation with standard JSON responses.
    Setup summary: Mock LLM response with JSON, call analyze, assert correct result parsing.
    """
    # Arrange
    mock_result: LanguageModelResponse = LanguageModelResponse(
        choices=[
            LanguageModelCompletionChoice(
                index=0,
                message=LanguageModelAssistantMessage(
                    content="""{
                        "value": "high",
                        "reason": "Test reason"
                    }"""
                ),
                finish_reason="stop",
            )
        ]
    )

    # Act
    with patch.object(
        context_relevancy_evaluator.language_model_service,
        "complete_async",
        return_value=mock_result,
    ) as mock_complete:
        result: EvaluationMetricResult = await context_relevancy_evaluator.analyze(
            sample_evaluation_input, basic_evaluation_config
        )

        # Assert
        assert isinstance(result, EvaluationMetricResult)
        assert result.value.lower() == "high"
        mock_complete.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_analyze__returns_valid_result__with_structured_output(
    context_relevancy_evaluator: MagicMock,
    sample_evaluation_input: EvaluationMetricInput,
    structured_evaluation_config: EvaluationMetricConfig,
) -> None:
    """
    Purpose: Verify analyze successfully processes structured output from LLM.
    Why this matters: Structured output provides more reliable parsing for evaluation results.
    Setup summary: Mock LLM response with structured output, call analyze with schema, assert parsing.
    """
    # Arrange
    mock_result: LanguageModelResponse = LanguageModelResponse(
        choices=[
            LanguageModelCompletionChoice(
                index=0,
                message=LanguageModelAssistantMessage(
                    content="HIGH",
                    parsed={"value": "high", "reason": "Test reason"},
                ),
                finish_reason="stop",
            )
        ]
    )
    structured_output_schema: type[EvaluationSchemaStructuredOutput] = (
        EvaluationSchemaStructuredOutput
    )

    # Act
    with patch.object(
        context_relevancy_evaluator.language_model_service,
        "complete_async",
        return_value=mock_result,
    ) as mock_complete:
        result: EvaluationMetricResult = await context_relevancy_evaluator.analyze(
            sample_evaluation_input,
            structured_evaluation_config,
            structured_output_schema,
        )

        # Assert
        assert isinstance(result, EvaluationMetricResult)
        assert result.value.lower() == "high"
        mock_complete.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_analyze__raises_evaluator_exception__with_invalid_structured_output(
    context_relevancy_evaluator: MagicMock,
    sample_evaluation_input: EvaluationMetricInput,
    structured_evaluation_config: EvaluationMetricConfig,
) -> None:
    """
    Purpose: Verify analyze raises exception when structured output fails validation.
    Why this matters: Invalid structured output should fail fast with clear error message.
    Setup summary: Mock LLM response with invalid schema data, assert EvaluatorException raised.
    """
    # Arrange
    mock_result: LanguageModelResponse = LanguageModelResponse(
        choices=[
            LanguageModelCompletionChoice(
                index=0,
                message=LanguageModelAssistantMessage(
                    content="HIGH", parsed={"invalid": "data"}
                ),
                finish_reason="stop",
            )
        ]
    )
    structured_output_schema: type[EvaluationSchemaStructuredOutput] = (
        EvaluationSchemaStructuredOutput
    )

    # Act & Assert
    with patch.object(
        context_relevancy_evaluator.language_model_service,
        "complete_async",
        return_value=mock_result,
    ):
        with pytest.raises(EvaluatorException) as exc_info:
            await context_relevancy_evaluator.analyze(
                sample_evaluation_input,
                structured_evaluation_config,
                structured_output_schema,
            )

        assert "Error occurred during structured output validation" in str(
            exc_info.value
        )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_analyze__raises_evaluator_exception__with_empty_response(
    context_relevancy_evaluator: MagicMock,
    sample_evaluation_input: EvaluationMetricInput,
    basic_evaluation_config: EvaluationMetricConfig,
) -> None:
    """
    Purpose: Verify analyze raises exception when LLM returns empty response content.
    Why this matters: Empty responses should fail fast with clear error message.
    Setup summary: Mock LLM response with empty content, assert EvaluatorException raised.
    """
    # Arrange
    mock_result: LanguageModelResponse = LanguageModelResponse(
        choices=[
            LanguageModelCompletionChoice(
                index=0,
                message=LanguageModelAssistantMessage(content=""),
                finish_reason="stop",
            )
        ]
    )

    # Act & Assert
    with patch.object(
        context_relevancy_evaluator.language_model_service,
        "complete_async",
        return_value=mock_result,
    ):
        with pytest.raises(EvaluatorException) as exc_info:
            await context_relevancy_evaluator.analyze(
                sample_evaluation_input, basic_evaluation_config
            )

        assert "did not return a result" in str(exc_info.value)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_analyze__raises_evaluator_exception__with_unknown_error(
    context_relevancy_evaluator: MagicMock,
    sample_evaluation_input: EvaluationMetricInput,
    basic_evaluation_config: EvaluationMetricConfig,
) -> None:
    """
    Purpose: Verify analyze handles unexpected errors gracefully with wrapped exception.
    Why this matters: Provides consistent error handling for all failure modes.
    Setup summary: Mock LLM to raise generic exception, assert EvaluatorException wrapper.
    """
    # Arrange - No additional setup needed

    # Act & Assert
    with patch.object(
        context_relevancy_evaluator.language_model_service,
        "complete_async",
        side_effect=Exception("Unknown error"),
    ):
        with pytest.raises(EvaluatorException) as exc_info:
            await context_relevancy_evaluator.analyze(
                sample_evaluation_input, basic_evaluation_config
            )

        assert "Unknown error occurred during context relevancy metric analysis" in str(
            exc_info.value
        )
