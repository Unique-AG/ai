import logging
from string import Template

from unique_toolkit.evaluators.config import (
    EvaluationMetricConfig,
)
from unique_toolkit.evaluators.exception import EvaluatorException
from unique_toolkit.evaluators.hallucination.constants import (
    SYSTEM_MSG_DEFAULT_KEY,
    SYSTEM_MSG_KEY,
    USER_MSG_DEFAULT_KEY,
    USER_MSG_KEY,
    hallucination_required_input_fields,
)
from unique_toolkit.evaluators.output_parser import (
    parse_eval_metric_result,
)
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricInput,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)
from unique_toolkit.language_model.service import LanguageModelService

from .prompts import (
    HALLUCINATION_METRIC_SYSTEM_MSG,
    HALLUCINATION_METRIC_SYSTEM_MSG_DEFAULT,
    HALLUCINATION_METRIC_USER_MSG,
    HALLUCINATION_METRIC_USER_MSG_DEFAULT,
)

logger = logging.getLogger(__name__)


async def check_hallucination_async(
    company_id: str,
    input: EvaluationMetricInput,
    config: EvaluationMetricConfig,
    logger: logging.Logger = logger,
) -> EvaluationMetricResult | None:
    """
    Analyzes the level of hallucination in the generated output by comparing it with the provided input
    and the contexts or history. The analysis classifies the hallucination level as:
    - low
    - medium
    - high

    If no contexts or history are referenced in the generated output, the method checks that the output
    does not contain any relevant information to answer the question.

    This method performs the following steps:
    1. Checks if the hallucination metric is enabled using the provided `config`.
    2. Logs the start of the analysis using the provided `logger`.
    3. Validates the required fields in the `input` data.
    4. Retrieves the messages using the `_get_msgs` method.
    5. Calls `LanguageModelService.complete_async_util` to get a completion result.
    6. Parses and returns the evaluation metric result based on the content of the completion result.

    Args:
        company_id (str): The company ID for the analysis.
        input (EvaluationMetricInput): The input data used for evaluation, including the generated output and reference information.
        config (EvaluationMetricConfig, optional): Configuration settings for the evaluation. Defaults to `hallucination_metric_default_config`.
        logger (Optional[logging.Logger], optional): The logger used for logging information and errors. Defaults to the logger for the current module.

    Returns:
        EvaluationMetricResult | None: The result of the evaluation, indicating the level of hallucination. Returns `None` if the metric is not enabled or if an error occurs.

    Raises:
        EvaluatorException: If the context texts are empty, required fields are missing, or an error occurs during the evaluation.
    """
    model_name = config.language_model.name
    logger.info(f"Analyzing level of hallucination with {model_name}.")

    input.validate_required_fields(hallucination_required_input_fields)

    try:
        msgs = _get_msgs(input, config, logger)
        result = await LanguageModelService.complete_async_util(
            company_id=company_id, messages=msgs, model_name=model_name
        )
        result_content = result.choices[0].message.content
        if not result_content:
            error_message = "Hallucination evaluation did not return a result."
            raise EvaluatorException(
                error_message=error_message,
                user_message=error_message,
            )
        return parse_eval_metric_result(
            result_content,  # type: ignore
            EvaluationMetricName.HALLUCINATION,
        )
    except Exception as e:
        error_message = "Error occurred during hallucination metric analysis"
        raise EvaluatorException(
            error_message=f"{error_message}: {e}",
            user_message=error_message,
            exception=e,
        )


def _get_msgs(
    input: EvaluationMetricInput,
    config: EvaluationMetricConfig,
    logger: logging.Logger,
):
    """
    Composes the messages for hallucination analysis based on the provided input and configuration.

    This method decides how to compose the messages based on the availability of context texts and history
    message texts in the `input`

    Args:
        input (EvaluationMetricInput): The input data that includes context texts and history message texts
                                      for the analysis.
        config (EvaluationMetricConfig): The configuration settings for composing messages.
        logger (Optional[logging.Logger], optional): The logger used for logging debug information.
                                                     Defaults to the logger for the current module.

    Returns:
        The composed messages as per the provided input and configuration. The exact type and structure
        depend on the implementation of the `compose_msgs` and `compose_msgs_default` methods.

    """
    if input.context_texts or input.history_messages:
        logger.debug("Using context / history for hallucination evaluation.")
        return _compose_msgs(input, config)
    else:
        logger.debug("No contexts and history provided for hallucination evaluation.")
        return _compose_msgs_default(input, config)


def _compose_msgs(
    input: EvaluationMetricInput,
    config: EvaluationMetricConfig,
):
    """
    Composes the hallucination analysis messages.
    """
    system_msg_content = _get_system_prompt_with_contexts(config)
    system_msg = LanguageModelSystemMessage(content=system_msg_content)

    user_msg_templ = Template(_get_user_prompt_with_contexts(config))
    user_msg_content = user_msg_templ.substitute(
        input_text=input.input_text,
        contexts_text=input.get_joined_context_texts(tag_name="reference"),
        history_messages_text=input.get_joined_history_texts(tag_name="conversation"),
        output_text=input.output_text,
    )
    user_msg = LanguageModelUserMessage(content=user_msg_content)
    return LanguageModelMessages([system_msg, user_msg])


def _compose_msgs_default(
    input: EvaluationMetricInput,
    config: EvaluationMetricConfig,
):
    """
    Composes the hallucination analysis prompt without messages.
    """
    system_msg_content = _get_system_prompt_default(config)
    system_msg = LanguageModelSystemMessage(content=system_msg_content)

    user_msg_templ = Template(_get_user_prompt_default(config))
    user_msg_content = user_msg_templ.substitute(
        input_text=input.input_text,
        output_text=input.output_text,
    )
    user_msg = LanguageModelUserMessage(content=user_msg_content)
    return LanguageModelMessages([system_msg, user_msg])


def _get_system_prompt_with_contexts(config: EvaluationMetricConfig):
    return config.custom_prompts.setdefault(
        SYSTEM_MSG_KEY,
        HALLUCINATION_METRIC_SYSTEM_MSG,
    )


def _get_user_prompt_with_contexts(config: EvaluationMetricConfig):
    return config.custom_prompts.setdefault(
        USER_MSG_KEY,
        HALLUCINATION_METRIC_USER_MSG,
    )


def _get_system_prompt_default(config: EvaluationMetricConfig):
    return config.custom_prompts.setdefault(
        SYSTEM_MSG_DEFAULT_KEY,
        HALLUCINATION_METRIC_SYSTEM_MSG_DEFAULT,
    )


def _get_user_prompt_default(config: EvaluationMetricConfig):
    return config.custom_prompts.setdefault(
        USER_MSG_DEFAULT_KEY,
        HALLUCINATION_METRIC_USER_MSG_DEFAULT,
    )
