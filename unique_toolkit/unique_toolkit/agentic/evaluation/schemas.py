from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from unique_toolkit.agentic.evaluation.exception import EvaluatorException
from unique_toolkit.chat import ChatMessage
from unique_toolkit.chat.schemas import (
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
)

_MAX_CODE_CHARS = 4000
_MAX_STDOUT_CHARS = 3000


class CodeExecutionContext(BaseModel):
    """Code and stdout from a single code interpreter call, used as grounding for hallucination evaluation."""

    code: str
    stdout: str = ""


class EvaluationMetricName(StrEnum):
    HALLUCINATION = "hallucination"
    CONTEXT_RELEVANCY = "relevancy"
    SUB_AGENT = "sub_agent"


class EvaluationMetricInputFieldName(StrEnum):
    INPUT_TEXT = "input_text"
    CONTEXT_TEXTS = "context_texts"
    HISTORY_MESSAGES = "history_messages"
    OUTPUT_TEXT = "output_text"


class EvaluationMetricInput(BaseModel):
    """
    Input for any metric evaluation. Depending on the metric, the input can be different.
    """

    input_text: Optional[str] = None
    context_texts: Optional[list[str]] = None
    history_messages: Optional[list[ChatMessage]] = None
    output_text: Optional[str] = None
    code_execution_contexts: Optional[list[CodeExecutionContext]] = None

    def get_joined_context_texts(self, tag_name: str = "reference") -> str:
        """
        Concatenates context_texts.
        """
        if not self.context_texts:
            return f"<No {tag_name} texts provided>"

        return "\n".join(
            [
                f"<{tag_name}-{index + 1}>{text}</{tag_name}-{index + 1}>"
                for index, text in enumerate(self.context_texts)
            ]
        )

    def get_history_message_text(self, chat_message: ChatMessage):
        return f"{chat_message.role.value}: {chat_message.content}"

    def get_history_message_texts(self) -> list[str]:
        if not self.history_messages:
            return []
        return [self.get_history_message_text(msg) for msg in self.history_messages]

    def get_joined_history_texts(self, tag_name: str = "conversation") -> str:
        """
        Concatenates history message texts.
        """
        if not self.history_messages:
            return f"<No {tag_name} texts provided>"

        return "\n".join(self.get_history_message_texts())

    def get_joined_code_contexts(self, tag_name: str = "code-execution") -> str:
        """
        Renders code execution contexts as tagged blocks for the hallucination judge.

        Each block contains the Python code that was executed and the captured stdout.
        Both are truncated if unusually long to stay within LLM context limits.
        """
        if not self.code_execution_contexts:
            return f"<No {tag_name} provided>"

        parts: list[str] = []
        for i, ctx in enumerate(self.code_execution_contexts):
            code = ctx.code
            if len(code) > _MAX_CODE_CHARS:
                code = (
                    code[:_MAX_CODE_CHARS]
                    + f"\n... [truncated — {len(ctx.code) - _MAX_CODE_CHARS} chars omitted]"
                )

            stdout = ctx.stdout if ctx.stdout else "(no output captured)"
            if len(stdout) > _MAX_STDOUT_CHARS:
                stdout = (
                    stdout[:_MAX_STDOUT_CHARS]
                    + f"\n... [truncated — {len(ctx.stdout) - _MAX_STDOUT_CHARS} chars omitted]"
                )

            code_block = f"```python\n{code}\n```"
            stdout_block = f"<stdout>\n{stdout}\n</stdout>"
            parts.append(
                f"<{tag_name}-{i + 1}>\n{code_block}\n{stdout_block}\n</{tag_name}-{i + 1}>"
            )

        return "\n".join(parts)

    def validate_required_fields(
        self, required_fields: list[EvaluationMetricInputFieldName]
    ):
        """
        Validates the input fields for the hallucination metric.
        """
        for field in required_fields:
            value = getattr(self, field)
            if value is None:
                error_message = f"Missing required input field: {field}"
                raise EvaluatorException(
                    user_message=error_message,
                    error_message=error_message,
                )


class EvaluationMetricResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: EvaluationMetricName
    value: str
    reason: str
    is_positive: Optional[bool] = None
    user_info: Optional[str] = None
    error: Exception | None = None
    fact_list: list[str] = Field(default_factory=list[str])


class EvaluationAssessmentMessage(BaseModel):
    status: ChatMessageAssessmentStatus
    explanation: str
    title: str
    label: ChatMessageAssessmentLabel
    type: ChatMessageAssessmentType
