from enum import Enum

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field, field_validator

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize, populate_by_name=True, arbitrary_types_allowed=True
)


class ChatMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    model_config = model_config

    id: str | None = None
    object: str | None = None
    content: str = Field(alias="text")
    role: ChatMessageRole
    debug_info: dict = {}

    # TODO make sdk return role consistently in lowercase
    # Currently needed as sdk returns role in uppercase
    @field_validator("role", mode="before")
    def set_role(cls, value: str):
        return value.lower()
