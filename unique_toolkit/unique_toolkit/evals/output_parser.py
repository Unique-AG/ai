from unique_toolkit.language_model.utils import convert_string_to_json

from _common.evaluators.context_relevancy.schema import (
    EvaluationSchemaStructuredOutput,
)
from _common.evaluators.exception import EvaluatorException
from _common.evaluators.schemas import (
    EvaluationMetricName,
    EvaluationMetricResult,
)


def parse_eval_metric_result(
    result: str,
    metric_name: EvaluationMetricName,
):
    """
    Parses the evaluation metric result.
    """

    try:
        parsed_result = convert_string_to_json(result)
    except Exception as e:
        error_message = (
            "Error occurred during parsing the evaluation metric result"
        )
        raise EvaluatorException(
            user_message=f"{error_message}.",
            error_message=f"{error_message}: {str(e)}",
        )

    return EvaluationMetricResult(
        name=metric_name,
        value=parsed_result.get("value", "None"),
        reason=parsed_result.get("reason", "None"),
    )


def parse_eval_metric_result_structured_output(
    result: EvaluationSchemaStructuredOutput,
    metric_name: EvaluationMetricName,
) -> EvaluationMetricResult:
    """
    Parses the evaluation metric result.
    """
    return EvaluationMetricResult(
        name=metric_name,
        value=result.value,
        reason=result.reason,
        fact_list=[item.fact for item in result.fact_list],
    )
