from datetime import datetime
from enum import StrEnum
from typing import Literal

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
    TOOL = "tool"  # TODO: Unused according @unique-fabian. To be removed in separate PR


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

    message_log_id: str | None = None
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
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChatMessage(BaseModel):
    # TODO: The below seems not to be True anymore @irina-unique. To be checked in separate PR
    # This model should strictly meets https://github.com/Unique-AG/monorepo/blob/master/node/apps/node-chat/src/public-api/2023-12-06/dtos/message/public-message.dto.ts
    model_config = model_config

    id: str | None = Field(description="The id of the message.", default=None)

    # Stream response can return a null previous_message_id if an assisstant message is manually added
    previous_message_id: str | None = Field(
        default=None, description="The id of the previous message in the chat."
    )
    chat_id: str = Field(description="The id of the chat that the message belongs to.")

    object: str | None = Field(
        default=None, description="The object of the message", examples=["message"]
    )
    text: str | None = Field(default=None, description="The text of the message")
    original_text: str | None = Field(
        default=None,
        description="The original text of the message. This is the text that a user or assistant originally entered before eventual modifications by the platform",
    )

    role: ChatMessageRole

    gpt_request: list[dict] | None = Field(
        default=None,
        description="The GPT request send to the model that resulted in this message. Only relevant for assistant messages.",
    )
    debug_info: dict | None = Field(
        default=None, description="The debug information of the message."
    )
    created_at: datetime | None = Field(
        default=None, description="The date and time the message was created."
    )
    updated_at: datetime | None = Field(
        default=None, description="The date and time the message was last updated."
    )
    completed_at: datetime | None = Field(
        default=None, description="The date and time the message was completed."
    )

    references: list[ContentReference] = Field(
        default=[], description="The references made within the message"
    )
    assessments: list[ChatMessageAssessment] = Field(
        default=[], description="The assessments made on the message in post-processing"
    )

    # Deprecated fields
    content: str | None = Field(
        deprecated="Use text instead", default=None, alias="text"
    )
    original_content: str | None = Field(
        deprecated="Use original_text instead", default=None, alias="originalText"
    )
    tool_calls: list[ToolCall] | None = Field(
        default=None,
        deprecated="Currently unused and will be removed in a future version",
        description="The tool calls of the message",
    )
    tool_call_id: str | None = Field(
        default=None,
        deprecated="Currently unused and will be removed in a future version",
        description="The tool call id of the message",
    )

    # TODO make sdk return role consistently in lowercase
    # Currently needed as sdk returns role in uppercase
    @field_validator("role", mode="before")
    def set_role(cls, value: str):
        return value.lower()

    # TODO: Deprecate the tool roles should be removed in separate PR
    # Ensure tool_call_ids is required if role is 'tool'
    @model_validator(mode="after")
    def check_tool_call_ids_for_tool_role(self):
        if self.role == ChatMessageRole.TOOL and not self.tool_call_id:
            raise ValueError("tool_call_ids is required when role is 'tool'")
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

            case ChatMessageRole.TOOL:
                raise NotImplementedError
