import json
from enum import StrEnum
from logging import getLogger
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar, override

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator
from pydantic_settings import BaseSettings
from typing_extensions import deprecated

from unique_toolkit._common.exception import ConfigurationException
from unique_toolkit.app.unique_settings import UniqueChatEventFilterOptions
from unique_toolkit.smart_rules.compile import UniqueQL, parse_uniqueql

FilterOptionsT = TypeVar("FilterOptionsT", bound=BaseSettings)

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)
_logger = getLogger(__name__)


class EventName(StrEnum):
    EXTERNAL_MODULE_CHOSEN = "unique.chat.external-module.chosen"
    USER_MESSAGE_CREATED = "unique.chat.user-message.created"
    INGESTION_CONTENT_UPLOADED = "unique.ingestion.content.uploaded"
    INGESTION_CONTENT_FINISHED = "unique.ingestion.content.finished"
    MAGIC_TABLE_IMPORT_COLUMNS = "unique.magic-table.import-columns"
    MAGIC_TABLE_ADD_META_DATA = "unique.magic-table.add-meta-data"
    MAGIC_TABLE_ADD_DOCUMENT = "unique.magic-table.add-document"
    MAGIC_TABLE_DELETE_ROW = "unique.magic-table.delete-row"
    MAGIC_TABLE_DELETE_COLUMN = "unique.magic-table.delete-column"
    MAGIC_TABLE_UPDATE_CELL = "unique.magic-table.update-cell"


class BaseEvent(BaseModel, Generic[FilterOptionsT]):
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

    def filter_event(self, *, filter_options: FilterOptionsT | None = None) -> bool:
        """Determine if event should be filtered out and be neglected."""
        return False


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
    user_prompt: Optional[str] = Field(
        default=None,
        description="An optional user prompt for the tool. This is a Unique specific field.",
    )
    tool_format_information: Optional[str] = Field(
        default=None,
        description="An optional tool format information. This is a Unique specific field.",
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
    user_prompt: Optional[str] = Field(
        default=None,
        description="An optional user prompt for the MCP server.",
    )
    tools: list[McpTool] = []


###
# ChatEvent schemas
###


class ChatEventUserMessage(BaseModel):
    model_config = model_config

    id: str = Field(
        description="The id of the user message. On an event this corresponds to the user message that created the event."
    )
    text: str = Field(description="The text of the user message.")
    original_text: str = Field(description="The original text of the user message.")
    created_at: str = Field(
        description="The creation date and time of the user message."
    )
    language: str = Field(description="The language of the user message.")


@deprecated(
    "Use `ChatEventUserMessage` instead. "
    "This class will be removed in the next major version."
)
class EventUserMessage(ChatEventUserMessage):
    """Deprecated: Use `ChatEventUserMessage` instead."""

    pass


class ChatEventAssistantMessage(BaseModel):
    model_config = model_config

    id: str = Field(
        description="The id of the assistant message. On an event this corresponds to the assistant message that will be returned by the process handling the event."
    )
    created_at: str = Field(
        description="The creation date and time of the assistant message."
    )


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
    message_execution_id: str | None = Field(
        default=None,
        description="The message execution id for triggering the chat event. Originates from the message execution service.",
    )
    session_config: JsonValue | None = Field(
        default=None,
        description="The session configuration for the chat session.",
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

    def get_initial_debug_info(self) -> dict[str, Any]:
        """Get the debug information for the chat event"""

        # TODO: Make sure this coincides with what is shown in the first user message
        return {
            "user_metadata": self.payload.user_metadata,
            "tool_parameters": self.payload.tool_parameters,
            "chosen_module": self.payload.name,
            "assistant": {"id": self.payload.assistant_id},
        }

    @override
    def filter_event(
        self, *, filter_options: UniqueChatEventFilterOptions | None = None
    ) -> bool:
        # Empty string evals to False

        if filter_options is None:
            return False  # Don't filter when no options provided

        if not filter_options.assistant_ids and not filter_options.references_in_code:
            raise ConfigurationException(
                "No filter options provided, all events will be filtered! \n"
                "Please define: \n"
                " - 'UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS' \n"
                " - 'UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE' \n"
                "in your environment variables."
            )

        # Per reference in code there can be multiple assistants
        if (
            filter_options.assistant_ids
            and self.payload.assistant_id not in filter_options.assistant_ids
        ):
            return True

        if (
            filter_options.references_in_code
            and self.payload.name not in filter_options.references_in_code
        ):
            return True

        return super().filter_event(filter_options=filter_options)


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
