"""Tests for evaluation metric output parsers."""

import pytest

from unique_toolkit.agentic.evaluation.context_relevancy.schema import (
    EvaluationSchemaStructuredOutput,
    Fact,
)
from unique_toolkit.agentic.evaluation.exception import EvaluatorException
from unique_toolkit.agentic.evaluation.output_parser import (
    parse_eval_metric_result,
    parse_eval_metric_result_structured_output,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationMetricName,
    EvaluationMetricResult,
)


@pytest.mark.ai
def test_parse_eval_metric_result__succeeds__with_all_fields() -> None:
    """
    Purpose: Verify parsing of complete evaluation metric JSON result with all fields.
    Why this matters: Core parsing functionality for evaluation results from LLM.
    Setup summary: Provide valid JSON with all fields, assert correct parsing and field values.
    """
    # Arrange
    result_json: str = '{"value": "high", "reason": "Test reason"}'
    metric_name: EvaluationMetricName = EvaluationMetricName.CONTEXT_RELEVANCY

    # Act
    parsed: EvaluationMetricResult = parse_eval_metric_result(result_json, metric_name)

    # Assert
    assert isinstance(parsed, EvaluationMetricResult)
    assert parsed.name == EvaluationMetricName.CONTEXT_RELEVANCY
    assert parsed.value == "high"
    assert parsed.reason == "Test reason"
    assert parsed.fact_list == []


@pytest.mark.ai
def test_parse_eval_metric_result__uses_default_reason__with_missing_field() -> None:
    """
    Purpose: Verify parsing handles missing optional fields by using defaults.
    Why this matters: Ensures robustness when LLM returns incomplete JSON responses.
    Setup summary: Provide JSON with only required field, assert default value for reason.
    """
    # Arrange
    result_json: str = '{"value": "high"}'
    metric_name: EvaluationMetricName = EvaluationMetricName.CONTEXT_RELEVANCY

    # Act
    parsed: EvaluationMetricResult = parse_eval_metric_result(result_json, metric_name)

    # Assert
    assert isinstance(parsed, EvaluationMetricResult)
    assert parsed.name == EvaluationMetricName.CONTEXT_RELEVANCY
    assert parsed.value == "high"
    assert parsed.reason == "None"
    assert parsed.fact_list == []


@pytest.mark.ai
def test_parse_eval_metric_result__raises_evaluator_exception__with_invalid_json() -> (
    None
):
    """
    Purpose: Verify parser raises appropriate exception for malformed JSON.
    Why this matters: Provides clear error handling for invalid LLM responses.
    Setup summary: Provide invalid JSON string, assert EvaluatorException with descriptive message.
    """
    # Arrange
    result_json: str = "invalid json"
    metric_name: EvaluationMetricName = EvaluationMetricName.CONTEXT_RELEVANCY

    # Act & Assert
    with pytest.raises(EvaluatorException) as exc_info:
        parse_eval_metric_result(result_json, metric_name)

    assert "Error occurred during parsing the evaluation metric result" in str(
        exc_info.value
    )


@pytest.mark.ai
def test_parse_eval_metric_result_structured_output__succeeds__without_fact_list() -> (
    None
):
    """
    Purpose: Verify parsing of structured output without optional fact list.
    Why this matters: Ensures structured output parsing works for basic evaluations.
    Setup summary: Create structured output object without facts, assert correct parsing.
    """
    # Arrange
    result: EvaluationSchemaStructuredOutput = EvaluationSchemaStructuredOutput(
        value="high", reason="Test reason"
    )
    metric_name: EvaluationMetricName = EvaluationMetricName.CONTEXT_RELEVANCY

    # Act
    parsed: EvaluationMetricResult = parse_eval_metric_result_structured_output(
        result, metric_name
    )

    # Assert
    assert isinstance(parsed, EvaluationMetricResult)
    assert parsed.name == EvaluationMetricName.CONTEXT_RELEVANCY
    assert parsed.value == "high"
    assert parsed.reason == "Test reason"
    assert parsed.fact_list == []


@pytest.mark.ai
def test_parse_eval_metric_result_structured_output__includes_facts__with_fact_list() -> (
    None
):
    """
    Purpose: Verify parsing of structured output with fact list extracts all facts.
    Why this matters: Fact extraction is critical for detailed evaluation feedback.
    Setup summary: Create structured output with multiple facts, assert all facts extracted.
    """
    # Arrange
    result: EvaluationSchemaStructuredOutput = EvaluationSchemaStructuredOutput(
        value="high",
        reason="Test reason",
        fact_list=[
            Fact(fact="Fact 1"),
            Fact(fact="Fact 2"),
        ],
    )
    metric_name: EvaluationMetricName = EvaluationMetricName.CONTEXT_RELEVANCY

    # Act
    parsed: EvaluationMetricResult = parse_eval_metric_result_structured_output(
        result, metric_name
    )

    # Assert
    assert isinstance(parsed, EvaluationMetricResult)
    assert parsed.name == EvaluationMetricName.CONTEXT_RELEVANCY
    assert parsed.value == "high"
    assert parsed.reason == "Test reason"
    assert parsed.fact_list == ["Fact 1", "Fact 2"]
    assert isinstance(parsed.fact_list, list)
    assert len(parsed.fact_list) == 2
