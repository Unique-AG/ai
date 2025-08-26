import logging

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.evals.config import EvaluationMetricConfig
from unique_toolkit.evals.schemas import EvaluationMetricInput, EvaluationMetricResult

from .constants import hallucination_metric_default_config
from .utils import check_hallucination

SYSTEM_MSG_KEY = "systemPrompt"
USER_MSG_KEY = "userPrompt"
SYSTEM_MSG_DEFAULT_KEY = "systemPromptDefault"
USER_MSG_DEFAULT_KEY = "userPromptDefault"


class HallucinationEvaluator:
    def __init__(self, event: ChatEvent):
        self.event = event

        self.logger = logging.getLogger(f"HallucinationEvaluator.{__name__}")

    async def analyze(
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

        return await check_hallucination(
            company_id=self.event.company_id, input=input, config=config
        )
