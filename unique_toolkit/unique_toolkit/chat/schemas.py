import json
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from humps import camelize
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_message_function_tool_call_param import (
    ChatCompletionMessageFunctionToolCallParam,
)
from openai.types.chat.chat_completion_message_function_tool_call_param import (
    Function as OpenAIFunction,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from unique_toolkit.content.schemas import ContentReference

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
)


class ChatMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"  # Note: These messages are appended by the backend and should not be confused with the LLM's system message.


class Function(BaseModel):
    model_config = model_config

    name: str
    arguments: str

    def to_openai(self) -> OpenAIFunction:
        return OpenAIFunction(
            arguments=self.arguments,
            name=self.name,
        )


class ToolCall(BaseModel):
    model_config = model_config

    id: str
    type: str
    function: Function

    def to_openai_param(self) -> ChatCompletionMessageFunctionToolCallParam:
        return ChatCompletionMessageFunctionToolCallParam(
            id=self.id,
            function=self.function.to_openai(),
            type="function",
        )


class ChatMessageToolResponse(BaseModel):
    """Persisted response for a single tool call."""

    model_config = model_config

    content: str
    id: str | None = None
    tool_call_id: str | None = None
    created_at: datetime | None = None


class ChatMessageTool(BaseModel):
    """Persisted record of one tool call issued during an agentic loop.

    Rows are ordered by ``round_index`` (sequential rounds) and
    ``sequence_index`` (position within a parallel batch).  Used by
    ``HistoryManager`` to reconstruct the full tool-call/response sequence
    on subsequent turns.
    """

    model_config = model_config

    id: str | None = None
    external_tool_call_id: str
    function_name: str
    arguments: dict[str, Any] | None = None
    round_index: int
    sequence_index: int
    message_id: str | None = None
    response: ChatMessageToolResponse | None = None
    created_at: datetime | None = None

    @field_validator("arguments", mode="before")
    @classmethod
    def parse_arguments(cls, value: Any) -> Any:
        if isinstance(value, str):
            return json.loads(value)
        return value


class ChatMessageAssessmentStatus(StrEnum):
    PENDING = "PENDING"
    DONE = "DONE"
    ERROR = "ERROR"


class ChatMessageAssessmentLabel(StrEnum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class ChatMessageAssessmentType(StrEnum):
    HALLUCINATION = "HALLUCINATION"
    COMPLIANCE = "COMPLIANCE"


class ChatMessageAssessment(BaseModel):
    model_config = model_config

    id: str
    object: str
    message_id: str
    status: ChatMessageAssessmentStatus
    type: ChatMessageAssessmentType
    title: str | None = None
    explanation: str | None = None
    label: ChatMessageAssessmentLabel | None = None
    is_visible: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChatMessage(BaseModel):
    # This model maps to PublicMessageDto from the backend public API:
    # next/services/node-chat/src/public-api/2023-12-06/dtos/message/public-message.dto.ts
    # Fields previous_message_id, tool_calls, tool_call_id are internal extensions not in the DTO.
    model_config = model_config

    id: str | None = None
    chat_id: str
    object: str | None = None
    # alias="text" applies only to construction (model_validate / __init__).
    # model_dump() uses the field name "content", not "text". Use model_dump(by_alias=True)
    # to get "text" as the key, or access via the .text property.
    content: str | None = Field(default=None, alias="text")
    original_text: str | None = None
    role: ChatMessageRole
    previous_message_id: str | None = None
    gpt_request: list[dict] | dict | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    debug_info: dict | None = {}
    created_at: datetime | None = None
    completed_at: datetime | None = None
    started_streaming_at: datetime | None = None
    stopped_streaming_at: datetime | None = None
    user_aborted_at: datetime | None = None
    updated_at: datetime | None = None
    references: list[ContentReference] | None = []
    assessment: list[ChatMessageAssessment] | None = None

    # TODO make sdk return role consistently in lowercase
    # Currently needed as sdk returns role in uppercase
    @field_validator("role", mode="before")
    def set_role(cls, value: str):
        return value.lower()

    @property
    def text(self) -> str | None:
        return self.content

    @text.setter
    def text(self, value: str | None) -> None:
        self.content = value

    # Ensure tool_call_id is required if role is 'tool'
    @model_validator(mode="after")
    def check_tool_call_ids_for_tool_role(self):
        if self.role == ChatMessageRole.TOOL and not self.tool_call_id:
            raise ValueError("tool_call_id is required when role is 'tool'")
        return self

    def to_openai_param(self) -> ChatCompletionMessageParam:
        match self.role:
            case ChatMessageRole.USER:
                return ChatCompletionUserMessageParam(
                    role="user",
                    content=self.content or "",
                )

            case ChatMessageRole.ASSISTANT:
                if self.tool_calls:
                    assistant_message = ChatCompletionAssistantMessageParam(
                        role="assistant",
                        audio=None,
                        content=self.content or "",
                        function_call=None,
                        refusal=None,
                        tool_calls=[t.to_openai_param() for t in self.tool_calls],
                    )
                else:
                    assistant_message = ChatCompletionAssistantMessageParam(
                        role="assistant",
                        audio=None,
                        content=self.content or "",
                        function_call=None,
                        refusal=None,
                    )

                return assistant_message

            case _:
                raise NotImplementedError(
                    f"to_openai_param not implemented for role: {self.role}"
                )


class MessageLogStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MessageExecutionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MessageExecutionType(StrEnum):
    DEEP_RESEARCH = "DEEP_RESEARCH"


class MessageExecutionUpdateStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MessageLogUncitedReferences(BaseModel):
    model_config = model_config
    data: list[ContentReference]


class MessageLogEvent(BaseModel):
    model_config = model_config
    type: Literal["WebSearch", "InternalSearch"]
    text: str


class MessageLogDetails(BaseModel):
    model_config = model_config
    data: list[MessageLogEvent] | None = None
    status: str | None = Field(
        default=None, description="Overarching status of the current message log"
    )


class MessageLog(BaseModel):
    model_config = model_config

    message_log_id: str | None = Field(default=None, validation_alias="id")
    message_id: str | None = None
    status: MessageLogStatus
    text: str | None = None
    details: MessageLogDetails | None = None
    uncited_references: MessageLogUncitedReferences | None = None
    order: int
    references: list[ContentReference] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MessageExecution(BaseModel):
    model_config = model_config

    message_execution_id: str | None = None
    message_id: str | None = None
    status: MessageExecutionStatus
    type: MessageExecutionType = MessageExecutionType.DEEP_RESEARCH
    seconds_remaining: int | None = None
    percentage_completed: int | None = None
    is_queueable: bool | None = None
    execution_options: dict | None = None
    progress_title: str | None = None
    position_in_queue: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
