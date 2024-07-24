from enum import StrEnum
from typing import Any

from humps import camelize
from pydantic import BaseModel, ConfigDict

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize, populate_by_name=True, arbitrary_types_allowed=True
)


class EventName(StrEnum):
    EXTERNAL_MODULE_CHOSEN = "unique.chat.external-module.chosen"


class EventUserMessage(BaseModel):
    model_config = model_config

    id: str
    text: str
    created_at: str


class EventAssistantMessage(BaseModel):
    model_config = model_config

    id: str
    created_at: str


class EventPayload(BaseModel):
    model_config = model_config

    name: EventName
    description: str
    configuration: dict[str, Any]
    chat_id: str
    assistant_id: str
    user_message: EventUserMessage
    assistant_message: EventAssistantMessage
    text: str | None = None


class Event(BaseModel):
    model_config = model_config

    id: str
    event: str
    user_id: str
    company_id: str
    payload: EventPayload
    created_at: int | None = None
    version: str | None = None
