from enum import StrEnum
from typing import Any, Optional

from humps import camelize
from pydantic import BaseModel, ConfigDict
from typing_extensions import deprecated

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)


class EventName(StrEnum):
    EXTERNAL_MODULE_CHOSEN = "unique.chat.external-module.chosen"


class BaseEvent(BaseModel):
    model_config = model_config

    id: str
    event: str
    user_id: str
    company_id: str


###
# ChatEvent schemas
###


class ChatEventUserMessage(BaseModel):
    model_config = model_config

    id: str
    text: str
    original_text: str
    created_at: str
    language: str


@deprecated(
    "Use `ChatEventUserMessage` instead. "
    "This class will be removed in the next major version."
)
class EventUserMessage(ChatEventUserMessage):
    """Deprecated: Use `ChatEventUserMessage` instead."""

    pass


class ChatEventAssistantMessage(BaseModel):
    model_config = model_config

    id: str
    created_at: str


@deprecated(
    "Use `ChatEventAssistantMessage` instead. "
    "This class will be removed in the next major version."
)
class EventAssistantMessage(ChatEventAssistantMessage):
    """Deprecated: Use `ChatEventAssistantMessage` instead."""

    pass


class ChatEventAdditionalParameters(BaseModel):
    model_config = model_config

    translate_to_language: Optional[str] = None
    content_id_to_translate: Optional[str] = None


@deprecated(
    "Use `ChatEventAdditionalParameters` instead. "
    "This class will be removed in the next major version."
)
class EventAdditionalParameters(ChatEventAdditionalParameters):
    """Deprecated: Use `ChatEventAdditionalParameters` instead."""

    pass


class ChatEventPayload(BaseModel):
    model_config = model_config

    name: str
    description: str
    configuration: dict[str, Any]
    chat_id: str
    assistant_id: str
    user_message: ChatEventUserMessage
    assistant_message: ChatEventAssistantMessage
    text: Optional[str] = None
    additional_parameters: Optional[ChatEventAdditionalParameters] = None
    user_metadata: Optional[dict[str, Any]] = None
    tool_parameters: Optional[dict[str, Any]] = None
    metadata_filter: Optional[dict[str, Any]] = None


@deprecated("""UUse `ChatEventPayload` instead.
            This class will be removed in the next major version.""")
class EventPayload(ChatEventPayload):
    user_message: EventUserMessage
    assistant_message: EventAssistantMessage
    additional_parameters: Optional[EventAdditionalParameters] = None


@deprecated(
    """Use the more specific `ChatEvent` instead that has the same properties. \
This class will be removed in the next major version."""
)
class Event(BaseModel):
    model_config = model_config

    id: str
    event: EventName
    user_id: str
    company_id: str
    payload: EventPayload
    created_at: Optional[int] = None
    version: Optional[str] = None


class ChatEvent(BaseEvent):
    model_config = model_config

    event: EventName
    payload: ChatEventPayload
    created_at: Optional[int] = None
    version: Optional[str] = None
