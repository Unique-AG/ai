from datetime import datetime
from enum import StrEnum

from humps import camelize
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize, populate_by_name=True, arbitrary_types_allowed=True
)


class ChatMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Function(BaseModel):
    model_config = model_config

    name: str
    arguments: str


class ToolCall(BaseModel):
    model_config = model_config

    id: str
    type: str
    function: Function


class ChatMessage(BaseModel):
    # This model should strictly meets https://github.com/Unique-AG/monorepo/blob/master/node/apps/node-chat/src/public-api/2023-12-06/dtos/message/public-message.dto.ts
    model_config = model_config

    id: str | None = None
    chat_id: str
    object: str | None = None
    content: str | None = Field(default=None, alias="text")
    original_content: str | None = Field(default=None, alias="originalText")
    role: ChatMessageRole
    gpt_request: list[dict] | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    debug_info: dict | None = {}
    created_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None

    # TODO make sdk return role consistently in lowercase
    # Currently needed as sdk returns role in uppercase
    @field_validator("role", mode="before")
    def set_role(cls, value: str):
        return value.lower()

    # Ensure tool_call_ids is required if role is 'tool'
    @model_validator(mode="after")
    def check_tool_call_ids_for_tool_role(self):
        if self.role == ChatMessageRole.TOOL and not self.tool_call_id:
            raise ValueError("tool_call_ids is required when role is 'tool'")
        return self


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
