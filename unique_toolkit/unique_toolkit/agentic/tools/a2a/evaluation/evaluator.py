import logging
from collections import defaultdict
from typing import override

import unique_sdk
from jinja2 import Template
from typing_extensions import TypedDict

from unique_toolkit.agentic.evaluation.evaluation_manager import Evaluation
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationAssessmentMessage,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.agentic.tools.a2a.evaluation.config import SubAgentEvaluationConfig
from unique_toolkit.agentic.tools.a2a.service import SubAgentTool
from unique_toolkit.chat.schemas import (
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
)
from unique_toolkit.language_model.builder import MessagesBuilder
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse
from unique_toolkit.language_model.service import LanguageModelService

logger = logging.getLogger(__name__)


class _SubAgentToolInfo(TypedDict):
    assessment: list[unique_sdk.Space.Assessment] | None
    display_name: str


NO_ASSESSMENTS_FOUND = "NO_ASSESSMENTS_FOUND"


class SubAgentsEvaluation(Evaluation):
    DISPLAY_NAME = "Sub Agents"

    def __init__(
        self,
        config: SubAgentEvaluationConfig,
        sub_agent_tools: list[SubAgentTool],
        language_model_service: LanguageModelService,
    ):
        super().__init__(EvaluationMetricName.SUB_AGENT)
        self._config = config

        self._assistant_id_to_tool_info: dict[str, _SubAgentToolInfo] = {}
        self._language_model_service = language_model_service

        for sub_agent_tool in sub_agent_tools:
            if sub_agent_tool.config.evaluation_config.display_evalution:
                sub_agent_tool.subscribe(self)
                self._assistant_id_to_tool_info[sub_agent_tool.config.assistant_id] = {
                    "assessment": None,
                    "display_name": sub_agent_tool.display_name(),
                }

    @override
    def get_assessment_type(self) -> ChatMessageAssessmentType:
        return self._config.assessment_type

    @override
    async def run(
        self, loop_response: LanguageModelStreamResponse
    ) -> EvaluationMetricResult:
        logger.info("Running sub agents evaluation")

        sub_agents_display_data = []

        value = ChatMessageAssessmentLabel.GREEN

        # Use a dict in order to compare labels (RED being the worst)
        label_comparison_dict = defaultdict(
            lambda: 3
        )  # Unkown labels are highest in the sorting
        label_comparison_dict[ChatMessageAssessmentLabel.GREEN] = 2
        label_comparison_dict[ChatMessageAssessmentLabel.YELLOW] = 1
        label_comparison_dict[ChatMessageAssessmentLabel.RED] = 0

        for assistant_id, tool_info in self._assistant_id_to_tool_info.items():
            assessments = tool_info["assessment"] or []
            valid_assessments = []
            for assessment in assessments:
                if (
                    assessment["label"] is None
                    or assessment["label"] not in ChatMessageAssessmentLabel
                ):
                    logger.warning(
                        "Unkown assistant label %s for assistant %s will be ignored",
                        assessment["label"],
                        assistant_id,
                    )
                    continue
                if assessment["status"] != ChatMessageAssessmentStatus.DONE:
                    logger.warning(
                        "Assessment %s for assistant %s is not done (status: %s) will be ignored",
                        assessment["label"],
                        assistant_id,
                    )
                    continue
                valid_assessments.append(assessment)

            if len(valid_assessments) == 0:
                logger.info("No valid assessment found for assistant %s", assistant_id)
                continue

            assessments = sorted(
                valid_assessments, key=lambda x: label_comparison_dict[x["label"]]
            )

            for assessment in assessments:
                value = min(
                    value, assessment["label"], key=lambda x: label_comparison_dict[x]
                )

            sub_agents_display_data.append(
                {
                    "name": tool_info["display_name"],
                    "assessments": assessments,
                }
            )

        if len(sub_agents_display_data) == 0:
            logger.warning("No valid sub agent assessments found")
            return EvaluationMetricResult(
                name=self.get_name(),
                value=NO_ASSESSMENTS_FOUND,
                reason="No sub agents assessments found",
            )

        should_summarize = False
        reason = ""

        if len(sub_agents_display_data) > 1:
            should_summarize = True
        elif len(sub_agents_display_data) == 1:
            if len(sub_agents_display_data[0]["assessments"]) > 1:
                should_summarize = True
            else:
                reason = (
                    sub_agents_display_data[0]["assessments"][0]["explanation"] or ""
                )

        if should_summarize:
            messages = (
                MessagesBuilder()
                .system_message_append(self._config.summarization_system_message)
                .user_message_append(
                    Template(self._config.summarization_user_message_template).render(
                        sub_agents=sub_agents_display_data,
                    )
                )
                .build()
            )

            reason = await self._language_model_service.complete_async(
                messages=messages,
                model_name=self._config.summarization_model.name,
                temperature=0.0,
            )
            reason = str(reason.choices[0].message.content)

        return EvaluationMetricResult(
            name=self.get_name(),
            value=value,
            reason=reason,
            is_positive=value == ChatMessageAssessmentLabel.GREEN,
        )

    @override
    async def evaluation_metric_to_assessment(
        self, evaluation_result: EvaluationMetricResult
    ) -> EvaluationAssessmentMessage:
        if evaluation_result.value == NO_ASSESSMENTS_FOUND:
            return EvaluationAssessmentMessage(
                status=ChatMessageAssessmentStatus.DONE,
                explanation="No valid sub agents assessments found to consolidate.",
                title=self.DISPLAY_NAME,
                label=ChatMessageAssessmentLabel.GREEN,
                type=self.get_assessment_type(),
            )

        return EvaluationAssessmentMessage(
            status=ChatMessageAssessmentStatus.DONE,
            explanation=evaluation_result.reason,
            title=self.DISPLAY_NAME,
            label=evaluation_result.value,  # type: ignore
            type=self.get_assessment_type(),
        )

    def notify_sub_agent_response(
        self, sub_agent_assistant_id: str, response: unique_sdk.Space.Message
    ) -> None:
        if sub_agent_assistant_id not in self._assistant_id_to_tool_info:
            logger.warning(
                "Unknown assistant id %s received, assessment will be ignored.",
                sub_agent_assistant_id,
            )
            return

        self._assistant_id_to_tool_info[sub_agent_assistant_id]["assessment"] = (
            response[
                "assessment"
            ].copy()  # Shallow copy as we don't modify individual assessments
            if response["assessment"] is not None
            else None
        )
