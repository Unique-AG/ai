from enum import Enum

from humps import camelize
from pydantic import BaseModel, ConfigDict

# set config to convert camelCase to snake_case
model_config = ConfigDict(alias_generator=camelize, populate_by_name=True, arbitrary_types_allowed=True)

class ChatMessageRole(str, Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"

class ChatMessage(BaseModel):
    model_config = model_config

    id: str
    object: str
    text: str
    role: ChatMessageRole
    gpt_request: str | None = None
    debug_info: dict = {}