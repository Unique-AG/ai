import regex as re

from unique_toolkit.agentic.evaluation.evaluation_manager import Evaluation
from unique_toolkit.agentic.evaluation.hallucination.constants import (
    HallucinationConfig,
)
from unique_toolkit.agentic.evaluation.hallucination.utils import check_hallucination
from unique_toolkit.agentic.evaluation.schemas import (
    EvaluationAssessmentMessage,
    EvaluationMetricInput,
    EvaluationMetricName,
    EvaluationMetricResult,
)
from unique_toolkit.agentic.reference_manager.reference_manager import (
    ReferenceManager,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat.schemas import (
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
)
from unique_toolkit.language_model.reference import _preprocess_message
from unique_toolkit.language_model.schemas import (
    LanguageModelStreamResponse,
)


class HallucinationEvaluation(Evaluation):
    def __init__(
        self,
        config: HallucinationConfig,
        event: ChatEvent,
        reference_manager: ReferenceManager,
    ):
        self.config = config
        self._company_id = event.company_id
        self._user_id = event.user_id
        self._reference_manager = reference_manager
        self._user_message = event.payload.user_message.text
        super().__init__(EvaluationMetricName.HALLUCINATION)

    async def run(
        self, loop_response: LanguageModelStreamResponse
    ) -> EvaluationMetricResult:  # type: ignore
        all_chunks = self._reference_manager.get_chunks()

        # source numbers from original text
        ref_pattern = r"\[(\d+)\]"
        original_text = loop_response.message.original_text

        # preprocess original text to deal with different source patterns
        original_text_preprocessed = _preprocess_message(original_text)

        source_number_matches = re.findall(ref_pattern, original_text_preprocessed)
        source_numbers = {int(num) for num in source_number_matches}

        referenced_chunks = [all_chunks[idx] for idx in source_numbers]

        evaluation_result: EvaluationMetricResult = await check_hallucination(
            company_id=self._company_id,
            user_id=self._user_id,
            input=EvaluationMetricInput(
                input_text=self._user_message,
                context_texts=[context.text for context in referenced_chunks],
                history_messages=[],  # TODO include loop_history messages
                output_text=loop_response.message.text,
            ),
            config=self.config,
        )

        # Get the label for the evaluation result
        score_value = evaluation_result.value.upper()
        label = getattr(
            self.config.score_to_label, score_value.lower(), "RED"
        )
        evaluation_result.is_positive = label != "RED"
        return evaluation_result

    def get_assessment_type(self) -> ChatMessageAssessmentType:
        return ChatMessageAssessmentType.HALLUCINATION

    async def evaluation_metric_to_assessment(
        self, evaluation_result: EvaluationMetricResult
    ) -> EvaluationAssessmentMessage:
        # Get title and label from score mappings
        score_value = evaluation_result.value.upper()
        title = getattr(
            self.config.score_to_title,
            score_value.lower(),
            evaluation_result.value,
        )
        label = ChatMessageAssessmentLabel(
            getattr(
                self.config.score_to_label,
                score_value.lower(),
                evaluation_result.value.upper(),
            )
        )
        status = (
            ChatMessageAssessmentStatus.DONE
            if not evaluation_result.error
            else ChatMessageAssessmentStatus.ERROR
        )
        explanation = evaluation_result.reason

        if status == ChatMessageAssessmentStatus.ERROR:
            title = "Hallucination Check Error"
            label = ChatMessageAssessmentLabel.RED
            explanation = (
                "An unrecoverable error occurred while evaluating the response."
            )

        return EvaluationAssessmentMessage(
            status=status,
            title=title,
            explanation=explanation,
            label=label,
            type=self.get_assessment_type(),
        )
