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
    object: str | None = None
    content: str = Field(alias="text")
    role: ChatMessageRole
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None
    debug_info: dict | None = {}

    # TODO make sdk return role consistently in lowercase
    # Currently needed as sdk returns role in uppercase
    @field_validator("role", mode="before")
    def set_role(cls, value: str):
        return value.lower()

    # Ensure tool_call_ids is required if role is 'tool'
    @model_validator(mode="after")
    @classmethod
    def check_tool_call_ids_for_tool_role(cls):
        if cls.role == ChatMessageRole.TOOL and not cls.tool_call_ids:
            raise ValueError("tool_call_ids is required when role is 'tool'")
        return cls
