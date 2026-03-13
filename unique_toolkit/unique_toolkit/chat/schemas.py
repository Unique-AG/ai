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
    SYSTEM = "system"  # Note: These messages are appended by the backend and should not be confused with the LLM’s system message.


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
    """The response produced by a single tool call execution.

    Persisted alongside the parent ``ChatMessageTool`` record in the backend
    ``MessageTool`` table.  ``content`` holds the raw string returned by the
    tool; it may be ``None`` when the tool was invoked but did not finish
    (e.g. the session ended mid-loop).
    """

    model_config = model_config

    id: str | None = None
    content: str | None = None
    tool_call_id: str | None = None
    created_at: datetime | None = None


class ChatMessageTool(BaseModel):
    """A persisted record of one tool call issued during an agentic loop.

    The backend ``MessageTool`` table stores one row per tool call.  Rows are
    grouped by the assistant ``message_id`` they belong to and ordered by
    ``round_index`` (which sequential round of tool-calling) and
    ``sequence_index`` (position within a parallel round).  On subsequent
    turns ``HistoryManager`` loads these records via
    ``ChatService.get_message_tools`` and reconstructs the full
    assistant → tool-call → tool-response message sequence so that the LLM
    context is correctly replayed.

    Attributes:
        id: Database primary key assigned by the backend (``None`` before
            persistence).
        external_tool_call_id: The ``id`` field carried in the
            ``LanguageModelFunctionCall`` as seen by the LLM (e.g.
            ``"call_abc123"``).  Used as the ``tool_call_id`` in matching
            ``LanguageModelToolMessage`` objects when replaying history.
        function_name: Name of the tool / function that was called.
        arguments: Decoded JSON arguments dict passed to the tool (may be
            ``None`` for tools that take no arguments).
        round_index: Zero-based index of the tool-calling round within the
            agentic loop turn.  All parallel tool calls in the same batch
            share the same ``round_index``.
        sequence_index: Zero-based position of this call within its round.
            Together with ``round_index`` this uniquely orders every tool
            call within a turn.
        message_id: ID of the parent assistant ``ChatMessage`` in the DB.
            Set after persistence; ``None`` before.
        response: The tool's response, or ``None`` if the tool was called
            but the session ended before a response was recorded.
        created_at: Server-side creation timestamp.
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


class ChatMessage(BaseModel):
    # TODO: The below seems not to be True anymore @irina-unique. To be checked in separate PR
    # This model should strictly meets https://github.com/Unique-AG/monorepo/blob/master/node/apps/node-chat/src/public-api/2023-12-06/dtos/message/public-message.dto.ts
    model_config = model_config

    id: str | None = None
    chat_id: str
    object: str | None = None
    content: str | None = Field(default=None, alias="text")
    original_content: str | None = Field(default=None, alias="originalText")
    role: ChatMessageRole
    gpt_request: list[dict] | dict | None = None
    tool_calls: list[ToolCall] | None = None
    debug_info: dict | None = {}
    created_at: datetime | None = None
    completed_at: datetime | None = None
    user_aborted_at: datetime | None = None
    updated_at: datetime | None = None
    references: list[ContentReference] | None = None

    # TODO make sdk return role consistently in lowercase
    # Currently needed as sdk returns role in uppercase
    @field_validator("role", mode="before")
    def set_role(cls, value: str):
        return value.lower()

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
