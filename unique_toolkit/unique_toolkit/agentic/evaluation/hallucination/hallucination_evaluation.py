from unique_toolkit.agentic.evaluation.evaluation_manager import Evaluation
from unique_toolkit.agentic.evaluation.hallucination.constants import (
    HallucinationConfig,
)
from unique_toolkit.agentic.evaluation.hallucination.utils import (
    check_hallucination,
    context_text_from_stream_response,
)
from unique_toolkit.agentic.evaluation.schemas import (
    CodeExecutionContext,
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
    ResponsesLanguageModelStreamResponse,
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

        # Extract context texts using existing utility function with bounds checking
        # This prevents IndexError from invalid source indices (e.g., from code blocks)
        context_texts = context_text_from_stream_response(
            response=loop_response,
            selected_chunks=all_chunks,
            source_selection_mode=self.config.source_selection_mode,
            reference_pattern=self.config.reference_pattern,
        )

        code_execution_contexts = _extract_code_execution_contexts(loop_response)

        evaluation_result: EvaluationMetricResult = await check_hallucination(
            company_id=self._company_id,
            user_id=self._user_id,
            input=EvaluationMetricInput(
                input_text=self._user_message,
                context_texts=context_texts,
                history_messages=[],  # TODO include loop_history messages
                output_text=loop_response.message.text,
                code_execution_contexts=code_execution_contexts or None,
            ),
            config=self.config,
        )

        score_to_label = self.config.score_to_label
        evaluation_result.is_positive = (
            score_to_label.get(evaluation_result.value.upper(), "RED") != "RED"
        )
        return evaluation_result

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


def _extract_code_execution_contexts(
    loop_response: LanguageModelStreamResponse,
) -> list[CodeExecutionContext]:
    """Extract code and stdout from code interpreter calls on the response.

    Returns an empty list when the response is not a ResponsesLanguageModelStreamResponse
    (e.g. the classic completions API path) or when no code interpreter calls are present.

    Stdout is only available when the fence feature flag is on
    (include=["code_interpreter_call.outputs"] is requested). When outputs are absent,
    code-only grounding is still useful for verifying the response is consistent with
    what was computed.
    """
    if not isinstance(loop_response, ResponsesLanguageModelStreamResponse):
        return []

    contexts: list[CodeExecutionContext] = []
    for call in loop_response.code_interpreter_calls:
        if not call.code:
            continue

        stdout = ""
        if call.outputs:
            stdout = "\n".join(
                output.logs for output in call.outputs if output.type == "logs"
            )

        contexts.append(CodeExecutionContext(code=call.code, stdout=stdout))

    return contexts
