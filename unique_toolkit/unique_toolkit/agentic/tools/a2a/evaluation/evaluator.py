import logging
from typing import NamedTuple, override

import unique_sdk
from jinja2 import Template
from pydantic import BaseModel

from unique_toolkit.agentic.evaluation.evaluation_manager import Evaluation
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationAssessmentMessage,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.agentic.tools.a2a.evaluation._utils import (
    get_valid_assessments,
    get_worst_label,
    sort_assessments,
)
from unique_toolkit.agentic.tools.a2a.evaluation.config import (
    SubAgentEvaluationConfig,
    SubAgentEvaluationServiceConfig,
)
from unique_toolkit.agentic.tools.a2a.response_watcher import (
    SubAgentResponse,
    SubAgentResponseWatcher,
)
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


class SubAgentEvaluationSpec(NamedTuple):
    display_name: str
    assistant_id: str
    config: SubAgentEvaluationConfig


_NO_ASSESSMENTS_FOUND = "NO_ASSESSMENTS_FOUND"


class _SingleAssessmentData(BaseModel):
    name: str
    explanation: str


def _format_single_assessment_found(name: str, explanation: str) -> str:
    return _SingleAssessmentData(name=name, explanation=explanation).model_dump_json()


@failsafe(failure_return_value=None, log_exceptions=False)
def _parse_single_assesment_found(value: str) -> _SingleAssessmentData | None:
    return _SingleAssessmentData.model_validate_json(value)


def _find_single_assessment(
    responses: dict[str, list[SubAgentResponse]],
) -> unique_sdk.Space.Assessment | None:
    if len(responses) == 1:
        sub_agent_responses = next(iter(responses.values()))
        if len(sub_agent_responses) == 1:
            response = sub_agent_responses[0].message
            if response["assessment"] is not None and len(response["assessment"]) == 1:
                return response["assessment"][0]

    return None


class SubAgentEvaluationService(Evaluation):
    DISPLAY_NAME = "Sub Agents"

    def __init__(
        self,
        config: SubAgentEvaluationServiceConfig,
        language_model_service: LanguageModelService,
        response_watcher: SubAgentResponseWatcher,
        evaluation_specs: list[SubAgentEvaluationSpec],
    ) -> None:
        super().__init__(EvaluationMetricName.SUB_AGENT)
        self._config = config

        self._response_watcher = response_watcher
        self._language_model_service = language_model_service

        self._evaluation_specs: dict[str, SubAgentEvaluationSpec] = {
            spec.assistant_id: spec
            for spec in evaluation_specs
            if spec.config.include_evaluation
        }

    @override
    def get_assessment_type(self) -> ChatMessageAssessmentType:
        return self._config.assessment_type

    def _get_included_sub_agent_responses(
        self,
    ) -> dict[str, list[SubAgentResponse]]:
        responses = {}
        for assistant_id, eval_spec in self._evaluation_specs.items():
            sub_agent_responses = self._response_watcher.get_responses(
                eval_spec.assistant_id
            )
            if len(sub_agent_responses) == 0:
                logger.debug(
                    "No responses for sub agent %s (%s)",
                    eval_spec.display_name,
                    eval_spec.assistant_id,
                )
                continue

            responses_with_assessment = []
            for response in sub_agent_responses:
                assessments = response.message["assessment"]

                if assessments is None or len(assessments) == 0:
                    logger.debug(
                        "No assessment for sub agent %s (%s) response with sequence number %s",
                        eval_spec.display_name,
                        eval_spec.assistant_id,
                        response.sequence_number,
                    )
                    continue

                assessments = get_valid_assessments(
                    assessments=assessments,
                    display_name=eval_spec.display_name,
                    sequence_number=response.sequence_number,
                )

                if len(assessments) > 0:
                    responses_with_assessment.append(response)

            responses[assistant_id] = responses_with_assessment

        return responses

    @override
    async def run(
        self, loop_response: LanguageModelStreamResponse
    ) -> EvaluationMetricResult:
        logger.info("Running sub agents evaluation")

        sub_agents_display_data = []

        responses = self._get_included_sub_agent_responses()

        # No valid assessments found
        if len(responses) == 0:
            logger.warning("No valid sub agent assessments found")

            return EvaluationMetricResult(
                name=self.get_name(),
                # This is a trick to be able to indicate to `evaluation_metric_to_assessment`
                # that no valid assessments were found
                value=_NO_ASSESSMENTS_FOUND,
                reason="No sub agents assessments found",
            )

        single_assessment = _find_single_assessment(responses)
        # Only one valid assessment found, no need to perform summarization
        if single_assessment is not None:
            assistant_id = next(iter(responses))
            explanation = single_assessment["explanation"] or ""
            name = self._evaluation_specs[assistant_id].display_name
            label = single_assessment["label"] or ""

            return EvaluationMetricResult(
                name=self.get_name(),
                value=label,
                # This is a trick to be able to pass the display name to the UI in `evaluation_metric_to_assessment`
                reason=_format_single_assessment_found(name, explanation),
                is_positive=label == ChatMessageAssessmentLabel.GREEN,
            )

        sub_agents_display_data = []

        # Multiple Assessments found
        value = ChatMessageAssessmentLabel.GREEN
        for assistant_id, sub_agent_responses in responses.items():
            display_name = self._evaluation_specs[assistant_id].display_name

            for response in sub_agent_responses:
                assessments = sort_assessments(response.message["assessment"])  #  type:ignore
                value = get_worst_label(value, assessments[0]["label"])  # type: ignore

                data = {
                    "name": display_name,
                    "assessments": assessments,
                }
                if len(sub_agent_responses) > 1:
                    data["name"] += f" {response.sequence_number}"

                sub_agents_display_data.append(data)

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

        single_assessment_data = _parse_single_assesment_found(evaluation_result.reason)
        if single_assessment_data is not None:
            return EvaluationAssessmentMessage(
                status=ChatMessageAssessmentStatus.DONE,
                explanation=single_assessment_data.explanation,
                title=single_assessment_data.name,
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
