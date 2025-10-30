import logging
from typing import override

import unique_sdk
from jinja2 import Template
from pydantic import BaseModel
from typing_extensions import TypedDict

from unique_toolkit.agentic.evaluation.evaluation_manager import Evaluation
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationAssessmentMessage,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.agentic.tools.a2a.evaluation._utils import (
    _get_valid_assessments,
    _sort_assessments,
    _worst_label,
)
from unique_toolkit.agentic.tools.a2a.evaluation.config import (
    SubAgentEvaluationConfig,
    SubAgentEvaluationServiceConfig,
)
from unique_toolkit.agentic.tools.a2a.tool import SubAgentTool
from unique_toolkit.agentic.tools.utils import failsafe
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
    assessments: dict[int, list[unique_sdk.Space.Assessment]]
    display_name: str


_NO_ASSESSMENTS_FOUND = "NO_ASSESSMENTS_FOUND"


class _SingleAssessmentData(BaseModel):
    name: str
    explanation: str


def _format_single_assessment_found(name: str, explanation: str) -> str:
    return _SingleAssessmentData(name=name, explanation=explanation).model_dump_json()


@failsafe(failure_return_value=False, log_exceptions=False)
def _is_single_assessment_found(value: str) -> bool:
    _ = _SingleAssessmentData.model_validate_json(value)
    return True


def _parse_single_assessment_found(value: str) -> tuple[str, str]:
    data = _SingleAssessmentData.model_validate_json(value)
    return data.name, data.explanation


class SubAgentEvaluationService(Evaluation):
    DISPLAY_NAME = "Sub Agents"

    def __init__(
        self,
        config: SubAgentEvaluationServiceConfig,
        language_model_service: LanguageModelService,
    ):
        super().__init__(EvaluationMetricName.SUB_AGENT)
        self._config = config

        self._assistant_id_to_tool_info: dict[str, _SubAgentToolInfo] = {}
        self._language_model_service = language_model_service

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

        for tool_info in self._assistant_id_to_tool_info.values():
            sub_agent_assessments = tool_info["assessments"] or []
            display_name = tool_info["display_name"]

            for sequence_number in sorted(sub_agent_assessments):
                assessments = sub_agent_assessments[sequence_number]

                valid_assessments = _get_valid_assessments(
                    assessments, display_name, sequence_number
                )
                if len(valid_assessments) == 0:
                    logger.info(
                        "No valid assessment found for assistant %s (sequence number: %s)",
                        display_name,
                        sequence_number,
                    )
                    continue

                assessments = _sort_assessments(valid_assessments)
                value = _worst_label(value, assessments[0]["label"])  # type: ignore

                data = {
                    "name": tool_info["display_name"],
                    "assessments": assessments,
                }
                if len(sub_agent_assessments) > 1:
                    data["name"] += f" {sequence_number}"

                sub_agents_display_data.append(data)

        # No valid assessments found
        if len(sub_agents_display_data) == 0:
            logger.warning("No valid sub agent assessments found")

            return EvaluationMetricResult(
                name=self.get_name(),
                # This is a trick to be able to indicate to `evaluation_metric_to_assessment`
                # that no valid assessments were found
                value=_NO_ASSESSMENTS_FOUND,
                reason="No sub agents assessments found",
            )

        # Only one valid assessment found, no need to perform summarization
        if (
            len(sub_agents_display_data) == 1
            and len(sub_agents_display_data[0]["assessments"]) == 1
        ):
            assessment = sub_agents_display_data[0]["assessments"][0]
            explanation = assessment["explanation"] or ""
            name = sub_agents_display_data[0]["name"]
            label = assessment["label"]

            return EvaluationMetricResult(
                name=self.get_name(),
                value=label,
                # This is a trick to be able to pass the display name to the UI in `evaluation_metric_to_assessment`
                reason=_format_single_assessment_found(name, explanation),
                is_positive=label == ChatMessageAssessmentLabel.GREEN,
            )

        reason = await self._get_reason(sub_agents_display_data)

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
        if evaluation_result.value == _NO_ASSESSMENTS_FOUND:
            return EvaluationAssessmentMessage(
                status=ChatMessageAssessmentStatus.DONE,
                explanation="No valid sub agents assessments found to consolidate.",
                title=self.DISPLAY_NAME,
                label=ChatMessageAssessmentLabel.GREEN,
                type=self.get_assessment_type(),
            )

        if _is_single_assessment_found(evaluation_result.reason):
            name, reason = _parse_single_assessment_found(evaluation_result.reason)
            return EvaluationAssessmentMessage(
                status=ChatMessageAssessmentStatus.DONE,
                explanation=reason,
                title=name,
                label=evaluation_result.value,  # type: ignore
                type=self.get_assessment_type(),
            )

        return EvaluationAssessmentMessage(
            status=ChatMessageAssessmentStatus.DONE,
            explanation=evaluation_result.reason,
            title=self.DISPLAY_NAME,
            label=evaluation_result.value,  # type: ignore
            type=self.get_assessment_type(),
        )

    def register_sub_agent_tool(
        self, tool: SubAgentTool, evaluation_config: SubAgentEvaluationConfig
    ) -> None:
        if not evaluation_config.include_evaluation:
            logger.warning(
                "Sub agent tool %s has evaluation config `include_evaluation` set to False, responses will be ignored.",
                tool.config.assistant_id,
            )
            return

        if tool.config.assistant_id not in self._assistant_id_to_tool_info:
            tool.subscribe(self)
            self._assistant_id_to_tool_info[tool.config.assistant_id] = (
                _SubAgentToolInfo(
                    display_name=tool.display_name(),
                    assessments={},
                )
            )

    def notify_sub_agent_response(
        self,
        response: unique_sdk.Space.Message,
        sub_agent_assistant_id: str,
        sequence_number: int,
    ) -> None:
        if sub_agent_assistant_id not in self._assistant_id_to_tool_info:
            logger.warning(
                "Unknown assistant id %s received, assessment will be ignored.",
                sub_agent_assistant_id,
            )
            return

        sub_agent_assessments = self._assistant_id_to_tool_info[sub_agent_assistant_id][
            "assessments"
        ]
        sub_agent_assessments[sequence_number] = (
            response[
                "assessment"
            ].copy()  # Shallow copy as we don't modify individual assessments
            if response["assessment"] is not None
            else []
        )

    async def _get_reason(self, sub_agents_display_data: list[dict]) -> str:
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

        return str(reason.choices[0].message.content)
