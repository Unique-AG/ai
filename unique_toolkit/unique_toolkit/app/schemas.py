import json
from enum import StrEnum
from pathlib import Path
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

    @classmethod
    def from_json_file(cls, file_path: Path) -> "BaseEvent":
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)


###
# MCP schemas
###

class McpTool(BaseModel):
    model_config = model_config

    name: str
    description: Optional[str] = None
    input_schema: dict[str, Any]
    output_schema: Optional[dict[str, Any]] = None
    annotations: Optional[dict[str, Any]] = None
    title: Optional[str] = Field(
        default=None,
        description="The display title for a tool. This is a Unique specific field.",
    )
    icon: Optional[str] = Field(
        default=None,
        description="An icon name from the Lucide icon set for the tool. This is a Unique specific field.",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="An optional system prompt for the tool. This is a Unique specific field.",
    )
    is_connected: bool = Field(
        description="Whether the tool is connected to the MCP server. This is a Unique specific field.",
    )

class McpServer(BaseModel):
    model_config = model_config

    id: str
    name: str
    system_prompt: Optional[str] = Field(
        default=None,
        description="An optional system prompt for the MCP server.",
    )
    tools: list[McpTool]

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
    text: str | None = None
    additional_parameters: ChatEventAdditionalParameters | None = None
    user_metadata: dict[str, Any] | None = Field(
        default_factory=dict,
    )
    tool_choices: list[str] = Field(
        default_factory=list,
        description="A list containing the tool names the user has chosen to be activated.",
    )
    disabled_tools: list[str] = Field(
        default_factory=list,
        description="A list containing the tool names of tools that are disabled at the company level",
    )
    tool_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters extracted from module selection function calling the tool.",
    )
    # Default is None as empty dict triggers error in `backend-ingestion`
    metadata_filter: dict[str, Any] | None = Field(
        default=None,
        description="Metadata filter compiled after module selection function calling and scope rules.",
    )
    raw_scope_rules: UniqueQL | None = Field(
        default=None,
        description="Raw UniqueQL rule that can be compiled to a metadata filter.",
    )
    mcp_servers: list[McpServer] = Field(
        default_factory=list,
        description="A list of MCP servers with tools available for the chat session.",
    )

    @field_validator("raw_scope_rules", mode="before")
    def validate_scope_rules(cls, value: dict[str, Any] | None) -> UniqueQL | None:
        if value:
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

    @classmethod
    def from_json_file(cls, file_path: Path) -> "ChatEvent":
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)


@deprecated(
    """Use the more specific `ChatEvent` instead that has the same properties. \
This class will be removed in the next major version."""
)
class Event(ChatEvent):
    pass
    # The below should only affect type hints
    # event: EventName T
    # payload: EventPayload

    @classmethod
    def from_json_file(cls, file_path: Path) -> "Event":
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)
