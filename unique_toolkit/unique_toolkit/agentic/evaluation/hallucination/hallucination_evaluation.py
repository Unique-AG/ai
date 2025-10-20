import regex as re
from unique_toolkit.unique_toolkit.content.schemas import ContentChunk

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
        referenced_source_numbers = self._extract_source_numbers(
            loop_response.message.original_text or ""
        )
        referenced_chunks = [all_chunks[source] for source in referenced_source_numbers]

        # referenced_chunks = self._reference_manager.get_latest_referenced_chunks()
        evaluation_result: EvaluationMetricResult = await check_hallucination(
            company_id=self._company_id,
            input=EvaluationMetricInput(
                input_text=self._user_message,
                context_texts=[context.text for context in referenced_chunks],
                history_messages=[],  # TODO include loop_history messages
                output_text=loop_response.message.text,
            ),
            config=self.config,
        )

        score_to_label = self.config.score_to_label
        evaluation_result.is_positive = (
            score_to_label.get(evaluation_result.value.upper(), "RED") != "RED"
        )
        return evaluation_result

    def _extract_source_numbers(self, text: str) -> set[int]:
        """
        Extract all source numbers from text citations in the format [sourceX].
        
        Args:
            text: Text containing source citations like [source0], [source1], etc.
            
        Returns:
            Set of source numbers found in the text
        """
        # Match patterns like [source0], [source1], etc.
        pattern = r'\[source(\d+)\]'
        matches = re.findall(pattern, text, re.IGNORECASE)
        return {int(num) for num in matches}

    def get_assessment_type(self) -> ChatMessageAssessmentType:
        return ChatMessageAssessmentType.HALLUCINATION

    async def evaluation_metric_to_assessment(
        self, evaluation_result: EvaluationMetricResult
    ) -> EvaluationAssessmentMessage:
        title = self.config.score_to_title.get(
            evaluation_result.value.upper(), evaluation_result.value
        )
        label = ChatMessageAssessmentLabel(
            self.config.score_to_label.get(
                evaluation_result.value.upper(), evaluation_result.value.upper()
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
