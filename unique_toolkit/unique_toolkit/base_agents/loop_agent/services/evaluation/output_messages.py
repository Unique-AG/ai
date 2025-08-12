from unique_toolkit.base_agents.loop_agent.services.evaluation.user_info_message import (
    EVALUATION_RESULT_MSG_TEMPLATE,
    EVALUATION_STATUS_MSG_TEMPLATE,
)
from unique_toolkit.evaluators.config import EvaluationMetricConfig
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricName,
    EvaluationMetricResult,
)


def get_eval_result_msg(
    evaluation_result: EvaluationMetricResult, config: EvaluationMetricConfig
):
    if not evaluation_result.value:
        return EVALUATION_STATUS_MSG_TEMPLATE.substitute(
            status="No result returned",
            title=config.name.value,
        )

    evaluation_score_to_title = config.score_to_title
    evaluation_score_value = evaluation_result.value.upper()
    evaluation_score_to_title_text = evaluation_score_to_title.get(
        f"{evaluation_score_value}", ""
    )
    evaluation_score = f"{evaluation_score_value} - {evaluation_score_to_title_text}"

    # ToDo: Make this more generic
    if config.name.value == EvaluationMetricName.HALLUCINATION.value:
        title = "Hallucination-Level"
    else:
        title = config.name.value

    return EVALUATION_RESULT_MSG_TEMPLATE.substitute(
        title=title,
        evaluation_score=evaluation_score,
        evaluation_score_reason=evaluation_result.reason,
    )
