import logging
from string import Template

from unique_toolkit.evaluators.config import (
    EvaluationMetricConfig,
)
from unique_toolkit.evaluators.context_relevancy.constants import (
    SYSTEM_MSG_KEY,
    USER_MSG_KEY,
    context_relevancy_required_input_fields,
)
from unique_toolkit.evaluators.context_relevancy.prompts import (
    CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG,
    CONTEXT_RELEVANCY_METRIC_USER_MSG,
)
from unique_toolkit.evaluators.exception import EvaluatorException
from unique_toolkit.evaluators.output_parser import (
    parse_eval_metric_result,
)
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricInput,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.language_model import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)
from unique_toolkit.language_model.service import LanguageModelService

logger = logging.getLogger(__name__)


async def check_context_relevancy_async(
    company_id: str,
    evaluation_metric_input: EvaluationMetricInput,
    config: EvaluationMetricConfig,
    logger: logging.Logger = logger,
) -> EvaluationMetricResult | None:
    """Analyzes the relevancy of the context provided for the given evaluation_metric_input and output.

    The analysis classifies the context relevancy level as:
    - low
    - medium
    - high

    This method performs the following steps:
    1. Logs the start of the analysis using the provided `logger`.
    2. Validates the required fields in the `evaluation_metric_input` data.
    3. Retrieves the messages using the `_get_msgs` method.
    4. Calls `LanguageModelService.complete_async_util` to get a completion result.
    5. Parses and returns the evaluation metric result based on the content of the completion result.

    Args:
        company_id (str): The company ID for the analysis.
        evaluation_metric_input (EvaluationMetricInput): The evaluation_metric_input data used for evaluation, including the generated output and reference information.
        config (EvaluationMetricConfig): Configuration settings for the evaluation.
        logger (Optional[logging.Logger], optional): The logger used for logging information and errors. Defaults to the logger for the current module.

    Returns:
        EvaluationMetricResult | None: The result of the evaluation, indicating the level of context relevancy. Returns `None` if an error occurs.

    Raises:
        EvaluatorException: If required fields are missing or an error occurs during the evaluation.

    """
    model_group_name = (
        config.language_model.name.value
        if isinstance(config.language_model.name, LanguageModelName)
        else config.language_model.name
    )
    logger.info(f"Analyzing context relevancy with {model_group_name}.")

    evaluation_metric_input.validate_required_fields(
        context_relevancy_required_input_fields,
    )

    if (
        evaluation_metric_input.context_texts
        and len(evaluation_metric_input.context_texts) == 0
    ):
        error_message = "No context texts provided."
        raise EvaluatorException(
            user_message=error_message,
            error_message=error_message,
        )

    try:
        msgs = _get_msgs(evaluation_metric_input, config)
        result = await LanguageModelService.complete_async_util(
            company_id=company_id,
            messages=msgs,
            model_name=model_group_name,
        )
        result_content = result.choices[0].message.content
        if not result_content:
            error_message = "Context relevancy evaluation did not return a result."
            raise EvaluatorException(
                error_message=error_message,
                user_message=error_message,
            )
        return parse_eval_metric_result(
            result_content,  # type: ignore
            EvaluationMetricName.CONTEXT_RELEVANCY,
        )
    except Exception as e:
        error_message = "Error occurred during context relevancy metric analysis"
        raise EvaluatorException(
            error_message=f"{error_message}: {e}",
            user_message=error_message,
            exception=e,
        )


def _get_msgs(
    evaluation_metric_input: EvaluationMetricInput,
    config: EvaluationMetricConfig,
) -> LanguageModelMessages:
    """Composes the messages for context relevancy analysis.

    The messages are based on the provided evaluation_metric_input and configuration.

    Args:
        evaluation_metric_input (EvaluationMetricInput): The evaluation_metric_input data that includes context texts for the analysis.
        config (EvaluationMetricConfig): The configuration settings for composing messages.

    Returns:
        LanguageModelMessages: The composed messages as per the provided evaluation_metric_input and configuration.

    """
    system_msg_content = _get_system_prompt(config)
    system_msg = LanguageModelSystemMessage(content=system_msg_content)

    user_msg_templ = Template(_get_user_prompt(config))
    user_msg_content = user_msg_templ.substitute(
        evaluation_metric_input_text=evaluation_metric_input.evaluation_metric_input_text,
        contexts_text=evaluation_metric_input.get_joined_context_texts(),
    )
    user_msg = LanguageModelUserMessage(content=user_msg_content)
    return LanguageModelMessages([system_msg, user_msg])


def _get_system_prompt(config: EvaluationMetricConfig):
    return config.custom_prompts.setdefault(
        SYSTEM_MSG_KEY,
        CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG,
    )


def _get_user_prompt(config: EvaluationMetricConfig):
    return config.custom_prompts.setdefault(
        USER_MSG_KEY,
        CONTEXT_RELEVANCY_METRIC_USER_MSG,
    )
