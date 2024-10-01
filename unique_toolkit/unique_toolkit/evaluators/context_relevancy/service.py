from logging import Logger

from unique_toolkit.app.schemas import Event
from unique_toolkit.evaluators.config import EvaluationMetricConfig
from unique_toolkit.evaluators.context_relevancy.constants import default_config
from unique_toolkit.evaluators.context_relevancy.utils import check_context_relevancy
from unique_toolkit.evaluators.schemas import (
    EvaluationMetricInput,
    EvaluationMetricResult,
)


class ContextRelevancyEvaluator:
    def __init__(
        self,
        event: Event,
        logger: Logger,
    ):
        self.event = event
        self.logger = logger

    async def run(
        self,
        input: EvaluationMetricInput,
        config: EvaluationMetricConfig = default_config,
    ) -> EvaluationMetricResult | None:
        """
        Analyzes the level of relevancy of a context by comparing
        it with the input text.

        Args:
            input (EvaluationMetricInput): The input for the metric.
            config (EvaluationMetricConfig): The configuration for the metric.

        Returns:
            EvaluationMetricResult | None: The result of the evaluation, indicating the level of context relevancy.
                                           Returns None if the metric is not enabled.

        Raises:
            EvaluatorException: If required fields are missing or an error occurs during evaluation.
        """
        if config.enabled is False:
            self.logger.info("Context relevancy metric is not enabled.")
            return None

        return await check_context_relevancy(
            company_id=self.event.company_id,
            input=input,
            config=config,
            logger=self.logger,
        )
