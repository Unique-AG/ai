from datetime import datetime
from enum import StrEnum
from typing import Optional

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
    model_config = model_config

    id: str | None = None
    chat_id: str
    object: str | None = None
    content: str = Field(alias="text")
    original_content: str | None = Field(alias="originalText")
    role: ChatMessageRole
    gptRequest: list[dict] | None = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None
    debug_info: dict | None = {}
    created_at: datetime
    completed_at: datetime | None = None
    updated_at: datetime

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


class MessageAssessmentStatus(StrEnum):
    PENDING = "PENDING"
    DONE = "DONE"
    ERROR = "ERROR"


class MessageAssessmentLabel(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"


class MessageAssessmentType(StrEnum):
    HALLUCINATION = "HALLUCINATION"
    COMPLIANCE = "COMPLIANCE"


class MessageAssessment(BaseModel):
    model_config = model_config

    id: str
    object: str
    message_id: str
    status: MessageAssessmentStatus
    type: MessageAssessmentType
    explanation: str | None = None
    label: MessageAssessmentLabel | None = None
    is_visible: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
