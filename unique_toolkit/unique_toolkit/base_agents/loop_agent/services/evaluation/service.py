import logging
from pathlib import Path

import humps
from unique_toolkit.chat import ChatMessageAssessmentType
from unique_toolkit.chat.service import (
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatService,
)
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.service import (
    LanguageModelService,
)
from unique_toolkit.unique_toolkit.base_agents.loop_agent.services.evaluation.config import EvaluationConfig
from unique_toolkit.unique_toolkit.base_agents.loop_agent.services.evaluation.output_messages import get_eval_result_msg
from unique_toolkit.unique_toolkit.base_agents.loop_agent.services.evaluation.user_info_message import HALLUCINATION_CHECK_FAILED_TEMPLATE, HALLUCINATION_CHECK_PASSED_TEMPLATE
from unique_toolkit.unique_toolkit.evaluators.config import EvaluationMetricConfig
from unique_toolkit.unique_toolkit.evaluators.hallucination.utils import check_hallucination
from unique_toolkit.unique_toolkit.evaluators.schemas import EvaluationMetricInput, EvaluationMetricName, EvaluationMetricResult
from unique_toolkit.unique_toolkit.tools.utils.execution.execution import SafeTaskExecutor



FOLDER_NAME = Path(__file__).parent.name
EXTERNAL_MODULE_NAME = humps.pascalize(FOLDER_NAME)
logger = logging.getLogger(f"{EXTERNAL_MODULE_NAME}.{__name__}")


class EvaluationService:
    def __init__(
        self,
        chat_service: ChatService,
        llm_service: LanguageModelService,
        config: EvaluationConfig,
        company_id: str,
        user_id: str,
    ):
        self.chat_service = chat_service
        self.llm_service = llm_service
        self.config = config
        self.company_id = company_id
        self.user_id = user_id

        self._task_executor = SafeTaskExecutor(logger=logger)

    def inform_user_about_negative_evaluation(self):
        """Inform the user about the negative evaluation and retry.

        Returns:
            The assistant message ID of the new assistant message.

        """
        self.chat_service.create_assistant_message(
            content="The response is not satisfactory. I will try again..."
        )

    async def run_evaluation_of_streaming_result(
        self,
        evaluation_check_list: list[EvaluationMetricName],
        chunks: list[ContentChunk],
        assistant_message_text: str,
        assistant_message_id: str,
        user_message_text: str,
    ) -> list[EvaluationMetricResult]:
        result = await self._task_executor.execute_async(
            self._run_evaluation_of_streaming_result,
            evaluation_check_list=evaluation_check_list,
            chunks=chunks,
            assistant_message_text=assistant_message_text,
            assistant_message_id=assistant_message_id,
            user_message_text=user_message_text,
        )

        if not result.success:
            await self._inform_user_error(
                assistant_message_id=assistant_message_id
            )

        return result.unpack(default=[])

    async def _run_evaluation_of_streaming_result(
        self,
        evaluation_check_list: list[EvaluationMetricName],
        chunks: list[ContentChunk],
        assistant_message_text: str,
        assistant_message_id: str,
        user_message_text: str,
    ) -> list[EvaluationMetricResult]:
        """
        Look at the produced result and check if the result is correct given all the available information. Depending on the used tools, there are different ways to evaluate the result.
        """
        if not evaluation_check_list:
            return []

        await self.chat_service.create_message_assessment_async(
            assistant_message_id=assistant_message_id,
            status=ChatMessageAssessmentStatus.PENDING,
            type=ChatMessageAssessmentType.HALLUCINATION,
        )
        evaluation_results = []

        for evaluation_check in evaluation_check_list:
            evaluation_result = await self._run_evaluation_check(
                evaluation_check=evaluation_check,
                assistant_message_text=assistant_message_text,
                assistant_message_id=assistant_message_id,
                user_message_text=user_message_text,
                chunks=chunks,
            )
            if evaluation_result is not None:
                evaluation_results.append(evaluation_result)

        return evaluation_results

    async def _run_evaluation_check(
        self,
        evaluation_check: EvaluationMetricName,
        assistant_message_text: str,
        assistant_message_id: str,
        user_message_text: str,
        chunks: list[ContentChunk],
    ) -> EvaluationMetricResult | None:
        """
        Run the evaluation check.
        """
        if evaluation_check == EvaluationMetricName.HALLUCINATION:
            evaluation_result = await self._perform_hallucination_check(
                chunks=chunks,
                assistant_message_text=assistant_message_text,
                user_message_text=user_message_text,
            )
        else:
            logger.error(f"Unknown evaluation check: {evaluation_check.value}")
            self.chat_service.modify_assistant_message(
                content="An error occurred while evaluating the response. The evaluation check is unknown."
            )
            return None

        evaluation_result.user_info = await self._process_evaluation_result(
            evaluation_result=evaluation_result,
            assistant_message_id=assistant_message_id,
        )
        return evaluation_result

    async def _perform_hallucination_check(
        self,
        chunks: list[ContentChunk],
        assistant_message_text: str,
        user_message_text: str,
    ) -> EvaluationMetricResult:
        """
        Perform the hallucination check and return the evaluation result.
        """
        evaluation_result: EvaluationMetricResult = await check_hallucination(
            logger=logger,
            company_id=self.company_id,
            input=EvaluationMetricInput(
                input_text=user_message_text,
                context_texts=[context.text for context in chunks],
                history_messages=[],  # TODO include loop_history messages
                output_text=assistant_message_text,
            ),
            config=self.config.hallucination_config,
        )

        score_to_label = self.config.hallucination_config.score_to_label
        evaluation_result.is_positive = (
            score_to_label.get(evaluation_result.value.upper(), "RED") != "RED"
        )
        return evaluation_result

    async def _process_evaluation_result(
        self,
        evaluation_result: EvaluationMetricResult,
        assistant_message_id: str,
    ) -> str:
        """
        Process the evaluation result and return a user info message.
        """
        await self._display_result_in_message_assessment(
            assistant_message_id=assistant_message_id,
            metric_result=evaluation_result,
            metric_config=self.config.hallucination_config,
        )

        evaluation_result_user_info = get_eval_result_msg(
            evaluation_result=evaluation_result,
            config=self.config.hallucination_config,
        )

        if not evaluation_result.is_positive:
            evaluation_result_user_info = (
                HALLUCINATION_CHECK_FAILED_TEMPLATE.substitute(
                    hallucination_result=evaluation_result_user_info
                )
            )
        else:
            evaluation_result_user_info = (
                HALLUCINATION_CHECK_PASSED_TEMPLATE.substitute(
                    hallucination_result=evaluation_result_user_info
                )
            )
        return evaluation_result_user_info

    async def _inform_user_error(
        self, assistant_message_id: str
    ) -> list[EvaluationMetricResult]:
        await self.chat_service.modify_message_assessment_async(
            assistant_message_id=assistant_message_id,
            status=ChatMessageAssessmentStatus.ERROR,
            explanation="An unrecoverable error occurred while evaluating the response.",
            type=ChatMessageAssessmentType.HALLUCINATION,  # For now hardcoded since we only support 1 check
        )
        return []

    async def _display_result_in_message_assessment(
        self,
        assistant_message_id: str,
        metric_result: EvaluationMetricResult,
        metric_config: EvaluationMetricConfig,
    ):
        await self.chat_service.modify_message_assessment_async(
            assistant_message_id=assistant_message_id,
            status=ChatMessageAssessmentStatus.DONE,
            explanation=metric_result.reason,
            title=metric_config.score_to_title[metric_result.value.upper()]
            if metric_config.score_to_title
            else None,
            label=ChatMessageAssessmentLabel(
                metric_config.score_to_label[metric_result.value.upper()]
            )
            if metric_config.score_to_label
            else None,
            type=ChatMessageAssessmentType.HALLUCINATION,
        )
