from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from unique_toolkit.chat import ChatMessage
from unique_toolkit.evaluators.exception import EvaluatorException


class EvaluationMetricName(Enum):
    HALLUCINATION = "hallucination"
    CONTEXT_RELEVANCY = "relevancy"


class EvaluationMetricInputFieldName(str, Enum):
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

    def get_joined_context_texts(self, tag_name: str = "reference") -> str:
        """
        Concatenates context_texts.
        """
        if not self.context_texts:
            return f"<No {tag_name} texts provided>"

        return "\n".join(
            [
                f"<{tag_name}-{index}>{text}</{tag_name}-{index}>"
                for index, text in enumerate(self.context_texts)
            ]
        )

    def get_history_message_text(self, chat_message: ChatMessage):
        return f"{chat_message.role.value}: {chat_message.content}"

    def get_history_message_texts(self):
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
