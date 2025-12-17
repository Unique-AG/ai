import asyncio
from abc import ABC
from logging import Logger

from unique_toolkit._common.execution import (
    Result,
    SafeTaskExecutor,
)
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationAssessmentMessage,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.chat.schemas import (
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
)
from unique_toolkit.chat.service import ChatService
from unique_toolkit.language_model.schemas import (
    LanguageModelStreamResponse,
)


class Evaluation(ABC):
    """
    Abstract base class for evaluation metrics.

    typical use cases include:
    - Hallucination checking
    - compliance checking
    """

    def __init__(self, name: EvaluationMetricName):
        self.name = name

    def get_name(self) -> EvaluationMetricName:
        return self.name

    def get_assessment_type(self) -> ChatMessageAssessmentType:
        raise NotImplementedError(
            "Subclasses must implement this method to return the assessment type."
        )

    async def run(
        self, loop_response: LanguageModelStreamResponse
    ) -> EvaluationMetricResult:
        raise NotImplementedError("Subclasses must implement this method.")

    async def evaluation_metric_to_assessment(
        self, evaluation_result: EvaluationMetricResult
    ) -> EvaluationAssessmentMessage:
        raise NotImplementedError(
            "Subclasses must implement this method to convert evaluation results to assessment messages."
        )


class EvaluationManager:
    """
    Manages the evaluation metrics and executes evaluation calls.

    This class is responsible for:
    - Storing and managing evaluation instances, identified by their unique names.
    - Executing selected evaluations asynchronously and processing their results.
    - Tracking the overall success or failure of evaluations.
    - Integrating with external services like logging and chat systems to display evaluation statuses and results.
    - Handling errors gracefully, including missing evaluations or failed executions.

    Key Features:
    - Evaluation Storage: Maintains a dictionary of evaluation instances for quick retrieval.
    - Asynchronous Execution: Supports concurrent execution of multiple evaluations for efficiency.
    - Result Processing: Tracks evaluation outcomes and updates the internal state based on results.
    - Chat Integration: Updates the chat interface with evaluation statuses and detailed assessments.
    - Error Handling: Provides robust error messages and fallback mechanisms for missing or failed evaluations.

    The EvaluationManager serves as the central hub for managing and executing evaluations.
    """

    # a hashmap to hold evaluations by their names

    def __init__(
        self,
        logger: Logger,
        chat_service: ChatService,
    ):
        self._logger = logger
        self._chat_service = chat_service
        self._evaluations: dict[EvaluationMetricName, Evaluation] = {}
        self._evaluation_passed: bool = True

    def add_evaluation(self, evaluation: Evaluation):
        self._evaluations[evaluation.get_name()] = evaluation

    def get_evaluation_by_name(self, name: EvaluationMetricName) -> Evaluation | None:
        return self._evaluations.get(name)

    async def run_evaluations(
        self,
        selected_evaluation_names: list[EvaluationMetricName],
        loop_response: LanguageModelStreamResponse,
        assistant_message_id: str,
    ) -> list[EvaluationMetricResult]:
        task_executor = SafeTaskExecutor(
            logger=self._logger,
        )

        tasks = [
            task_executor.execute_async(
                self.execute_evaluation_call,
                loop_response=loop_response,
                evaluation_name=evaluation_name,
                assistant_message_id=assistant_message_id,
            )
            for evaluation_name in selected_evaluation_names
        ]
        evaluation_results = await asyncio.gather(*tasks)
        evaluation_results_unpacked: list[EvaluationMetricResult] = []

        for i, result in enumerate(evaluation_results):
            unpacked_evaluation_result = self._create_evaluation_metric_result(
                result, selected_evaluation_names[i]
            )
            if not unpacked_evaluation_result.is_positive:
                self._evaluation_passed = False
            evaluation_results_unpacked.append(unpacked_evaluation_result)

        for evaluation_name, evaluation_result in zip(
            selected_evaluation_names, evaluation_results_unpacked
        ):
            evaluation_instance = self.get_evaluation_by_name(evaluation_name)
            if evaluation_instance:
                await self._show_message_assessment(
                    evaluation_instance, evaluation_result, assistant_message_id
                )

        return evaluation_results_unpacked

    async def execute_evaluation_call(
        self,
        evaluation_name: EvaluationMetricName,
        loop_response: LanguageModelStreamResponse,
        assistant_message_id: str,
    ) -> EvaluationMetricResult:
        self._logger.info(f"Processing tool call: {evaluation_name}")

        evaluation_instance = self.get_evaluation_by_name(evaluation_name)

        if evaluation_instance:
            # Execute the evaluation
            await self._create_assistant_message(
                evaluation_instance, assistant_message_id
            )
            evaluation_metric_result: EvaluationMetricResult = (
                await evaluation_instance.run(loop_response)
            )
            return evaluation_metric_result

        return EvaluationMetricResult(
            name=evaluation_name,
            is_positive=True,
            value="RED",
            reason=f"Evaluation named {evaluation_name} not found",
            error=Exception("Evaluation named {evaluation_name} not found"),
        )

    def _create_evaluation_metric_result(
        self,
        result: Result[EvaluationMetricResult],
        evaluation_name: EvaluationMetricName,
    ) -> EvaluationMetricResult:
        if not result.success:
            return EvaluationMetricResult(
                name=evaluation_name,
                is_positive=True,
                value="RED",
                reason=str(result.exception),
                error=Exception("Evaluation result is not successful"),
            )
        unpacked = result.unpack()
        if not isinstance(unpacked, EvaluationMetricResult):
            return EvaluationMetricResult(
                name=evaluation_name,
                is_positive=True,
                value="RED",
                reason="Evaluation result is not of type EvaluationMetricResult",
                error=Exception(
                    "Evaluation result is not of type EvaluationMetricResult"
                ),
            )
        return unpacked

    async def _show_message_assessment(
        self,
        evaluation_instance: Evaluation,
        evaluation_metric_result: EvaluationMetricResult,
        assistant_message_id: str,
    ) -> None:
        evaluation_assessment_message = (
            await evaluation_instance.evaluation_metric_to_assessment(
                evaluation_metric_result
            )
        )
        await self._chat_service.modify_message_assessment_async(
            assistant_message_id=assistant_message_id,
            status=evaluation_assessment_message.status,
            title=evaluation_assessment_message.title,
            explanation=evaluation_assessment_message.explanation,
            label=evaluation_assessment_message.label,
            type=evaluation_assessment_message.type,
        )

    async def _create_assistant_message(
        self, evaluation_instance: Evaluation, assistant_message_id: str
    ):
        await self._chat_service.create_message_assessment_async(
            assistant_message_id=assistant_message_id,
            status=ChatMessageAssessmentStatus.PENDING,
            type=evaluation_instance.get_assessment_type(),
        )
