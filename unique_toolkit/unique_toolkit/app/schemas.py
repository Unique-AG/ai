from enum import StrEnum
from typing import Any, Optional

from humps import camelize
from pydantic import BaseModel, ConfigDict

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)


class EventName(StrEnum):
    EXTERNAL_MODULE_CHOSEN = "unique.chat.external-module.chosen"


class EventUserMessage(BaseModel):
    model_config = model_config

    id: str
    text: str
    original_text: str
    created_at: str
    language: str


class EventAssistantMessage(BaseModel):
    model_config = model_config

    id: str
    created_at: str


class EventAdditionalParameters(BaseModel):
    model_config = model_config

    translate_to_language: Optional[str] = None
    content_id_to_translate: Optional[str] = None


class EventPayload(BaseModel):
    model_config = model_config

    name: str
    description: str
    configuration: dict[str, Any]
    chat_id: str
    assistant_id: str
    user_message: EventUserMessage
    assistant_message: EventAssistantMessage
    text: Optional[str] = None
    additional_parameters: Optional[EventAdditionalParameters] = None
    user_metadata: Optional[dict[str, Any]] = None
    tool_parameters: Optional[dict[str, Any]] = None
    metadata_filter: Optional[dict[str, Any]] = None


class Event(BaseModel):
    model_config = model_config

    id: str
    event: EventName
    user_id: str
    company_id: str
    payload: EventPayload
    created_at: Optional[int] = None
    version: Optional[str] = None


class BaseEvent(BaseModel):
    model_config = model_config

    id: str
    event: str
    user_id: str
    company_id: str


class ChatEvent(BaseEvent):
    model_config = model_config

    event: EventName
    payload: EventPayload
    created_at: Optional[int] = None
    version: Optional[str] = None


class MagicTableEvent(BaseEvent):
    model_config = model_config
