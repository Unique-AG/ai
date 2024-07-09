from typing import Any

from humps import camelize
from pydantic import BaseModel, ConfigDict

# set config to convert camelCase to snake_case
model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)

class UserMessage(BaseModel):
    model_config = model_config

    id: str
    text: str
    created_at: str


class AssistantMessage(BaseModel):
    model_config = model_config

    id: str
    created_at: str


class Payload(BaseModel):
    model_config = model_config

    name: str
    description: str
    configuration: dict[str, Any]
    chat_id: str
    assistant_id: str
    user_message: UserMessage
    assistant_message: AssistantMessage
    text: str | None = None


class Event(BaseModel):
    model_config = model_config

    id: str
    version: str
    event: str
    created_at: int
    user_id: str
    company_id: str
    payload: Payload