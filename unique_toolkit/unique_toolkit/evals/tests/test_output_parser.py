import pytest

from _common.evaluators.context_relevancy.schema import (
    EvaluationSchemaStructuredOutput,
    Fact,
)
from _common.evaluators.exception import EvaluatorException
from _common.evaluators.output_parser import (
    parse_eval_metric_result,
    parse_eval_metric_result_structured_output,
)
from _common.evaluators.schemas import (
    EvaluationMetricName,
    EvaluationMetricResult,
)


def test_parse_eval_metric_result_success():
    # Test successful parsing with all fields
    result = '{"value": "high", "reason": "Test reason"}'
    parsed = parse_eval_metric_result(
        result, EvaluationMetricName.CONTEXT_RELEVANCY
    )

    assert isinstance(parsed, EvaluationMetricResult)
    assert parsed.name == EvaluationMetricName.CONTEXT_RELEVANCY
    assert parsed.value == "high"
    assert parsed.reason == "Test reason"
    assert parsed.fact_list == []


def test_parse_eval_metric_result_missing_fields():
    # Test parsing with missing fields (should use default "None")
    result = '{"value": "high"}'
    parsed = parse_eval_metric_result(
        result, EvaluationMetricName.CONTEXT_RELEVANCY
    )

    assert isinstance(parsed, EvaluationMetricResult)
    assert parsed.name == EvaluationMetricName.CONTEXT_RELEVANCY
    assert parsed.value == "high"
    assert parsed.reason == "None"
    assert parsed.fact_list == []


def test_parse_eval_metric_result_invalid_json():
    # Test parsing with invalid JSON
    result = "invalid json"
    with pytest.raises(EvaluatorException) as exc_info:
        parse_eval_metric_result(
            result, EvaluationMetricName.CONTEXT_RELEVANCY
        )

    assert "Error occurred during parsing the evaluation metric result" in str(
        exc_info.value
    )


def test_parse_eval_metric_result_structured_output_basic():
    # Test basic structured output without fact list
    result = EvaluationSchemaStructuredOutput(
        value="high", reason="Test reason"
    )
    parsed = parse_eval_metric_result_structured_output(
        result, EvaluationMetricName.CONTEXT_RELEVANCY
    )

    assert isinstance(parsed, EvaluationMetricResult)
    assert parsed.name == EvaluationMetricName.CONTEXT_RELEVANCY
    assert parsed.value == "high"
    assert parsed.reason == "Test reason"
    assert parsed.fact_list == []


def test_parse_eval_metric_result_structured_output_with_facts():
    # Test structured output with fact list
    result = EvaluationSchemaStructuredOutput(
        value="high",
        reason="Test reason",
        fact_list=[
            Fact(fact="Fact 1"),
            Fact(fact="Fact 2"),
        ],
    )
    parsed = parse_eval_metric_result_structured_output(
        result, EvaluationMetricName.CONTEXT_RELEVANCY
    )

    assert isinstance(parsed, EvaluationMetricResult)
    assert parsed.name == EvaluationMetricName.CONTEXT_RELEVANCY
    assert parsed.value == "high"
    assert parsed.reason == "Test reason"
    assert parsed.fact_list == ["Fact 1", "Fact 2"]
    assert isinstance(parsed.fact_list, list)
    assert len(parsed.fact_list) == 2  # None fact should be filtered out
