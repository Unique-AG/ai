from enum import StrEnum
from typing import Any, Optional

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing_extensions import deprecated

from unique_toolkit.smart_rules.compile import UniqueQL, parse_uniqueql

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
    tool_choices: Optional[list[str]] = Field(
        default=[],
        description="A list containing the tool names the user has chosen to be activated.",
    )
    tool_parameters: Optional[dict[str, Any]] = None
    metadata_filter: Optional[dict[str, Any]] = None
    raw_scope_rules: UniqueQL | None = Field(
        default=None,
        description="Raw UniqueQL rule that can be compiled to a metadata filter.",
    )

    @field_validator("raw_scope_rules", mode="before")
    def validate_scope_rules(cls, value: dict[str, Any]) -> UniqueQL:
        return parse_uniqueql(value)


@deprecated("""Use `ChatEventPayload` instead.
            This class will be removed in the next major version.""")
class EventPayload(ChatEventPayload):
    pass
    # user_message: EventUserMessage
    # assistant_message: EventAssistantMessage
    # additional_parameters: Optional[EventAdditionalParameters] = None


class ChatEvent(BaseEvent):
    model_config = model_config

    payload: ChatEventPayload
    created_at: Optional[int] = None
    version: Optional[str] = None


@deprecated(
    """Use the more specific `ChatEvent` instead that has the same properties. \
This class will be removed in the next major version."""
)
class Event(ChatEvent):
    pass
    # The below should only affect type hints
    # event: EventName T
    # payload: EventPayload
