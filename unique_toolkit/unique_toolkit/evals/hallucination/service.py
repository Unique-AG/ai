import logging

from quart import g, has_app_context
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.evals.config import EvaluationMetricConfig
from unique_toolkit.evals.exception import EvaluatorException
from unique_toolkit.evals.output_parser import parse_eval_metric_result
from unique_toolkit.evals.schemas import (
    EvaluationMetricInput,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.language_model.service import LanguageModelService
from unique_toolkit.reference_manager.reference_manager import (
    ReferenceManager,
)


from .constants import hallucination_metric_default_config
from .utils import _get_msgs, check_hallucination

SYSTEM_MSG_KEY = "systemPrompt"
USER_MSG_KEY = "userPrompt"
SYSTEM_MSG_DEFAULT_KEY = "systemPromptDefault"
USER_MSG_DEFAULT_KEY = "userPromptDefault"


class HallucinationEvaluator:
    def __init__(
        self,
        logger: logging.Logger,
        config: EvaluationMetricConfig,
        reference_manager: ReferenceManager,
        language_model_service: LanguageModelService,
        question: str,
        event: ChatEvent,
    ):
        self.logger = logger
        self.config = config
        self.question = question
        self.reference_manager = reference_manager
        self.logger = logger
        self.companyId = event.company_id
        self.language_model_service = language_model_service

    async def run(
        self,
        input: EvaluationMetricInput,
        config: EvaluationMetricConfig = hallucination_metric_default_config,
    ) -> EvaluationMetricResult | None:
        """
        Analyzes the level of hallucination in the generated output by comparing it with the input
        and the provided contexts or history. The analysis classifies the hallucination level as:
        - low
        - medium
        - high

        If no contexts or history are referenced in the generated output, the method verifies
        that the output does not contain any relevant information to answer the question.

        This method calls `check_hallucination` to perform the actual analysis. The `check_hallucination`
        function handles the evaluation using the company ID from the event, the provided input, and the configuration.

        Args:
            input (EvaluationMetricInput): The input data used for evaluation, including the generated output and reference information.
            config (EvaluationMetricConfig, optional): Configuration settings for the evaluation. Defaults to `hallucination_metric_default_config`.

        Returns:
            EvaluationMetricResult | None: The result of the evaluation, indicating the level of hallucination. Returns `None` if the analysis cannot be performed.

        Raises:
            EvaluatorException: If the context texts are empty, required fields are missing, or an error occurs during the evaluation.
        """
        if config.enabled is False:
            self.logger.info("Hallucination metric is not enabled.")
            return None

        return await self.check_hallucination(input)

    async def check_hallucination(
        self,
        input: EvaluationMetricInput,
    ) -> EvaluationMetricResult:
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

        model_name = self.config.language_model.name
        self.logger.info(f"Analyzing level of hallucination with {model_name}.")

        input.validate_required_fields(hallucination_required_input_fields)

        try:
            msgs = _get_msgs(input, self.config, self.logger)
            result = await self.language_model_service.complete_async(
                messages=msgs, model_name=model_name
            )

            result_content = result.choices[0].message.content
            # check that result content is a string
            if not isinstance(result_content, str):
                error_message = "Hallucination evaluation result is not a string."
                raise EvaluatorException(error_message, error_message)

            if not result_content:
                error_message = "Hallucination evaluation did not return a result."
                raise EvaluatorException(error_message, error_message)

            return parse_eval_metric_result(
                result_content,
                EvaluationMetricName.HALLUCINATION,
            )
        except Exception as e:
            error_message = "Error occurred during hallucination metric analysis"
            raise EvaluatorException(
                error_message=f"{error_message}: {e}",
                user_message=error_message,
                exception=e,
            )
