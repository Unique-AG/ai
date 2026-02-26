from datetime import datetime
from enum import StrEnum
from typing import Any

from humps import camelize
from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_serializer

# set config to convert camelCase to snake_case
model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
)


class ElicitationObject(StrEnum):
    ELICITATION = "elicitation"


class ElicitationMode(StrEnum):
    FORM = "FORM"
    URL = "URL"


class ElicitationAction(StrEnum):
    ACCEPT = "ACCEPT"
    DECLINE = "DECLINE"
    CANCEL = "CANCEL"


class ElicitationStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ElicitationSource(StrEnum):
    API = "INTERNAL_TOOL"
    MCP = "MCP_SERVER"


class Elicitation(BaseModel):
    """
    Represents an elicitation request.
    """

    model_config = model_config

    id: str = Field(description="Unique identifier for the elicitation")
    object: ElicitationObject = Field(description="Object type, always 'elicitation'")
    source: ElicitationSource = Field(
        description="Source of the elicitation (API or MCP)"
    )
    mode: ElicitationMode = Field(description="Elicitation mode: FORM or URL")
    status: ElicitationStatus = Field(
        description="Current status of the elicitation request"
    )
    message: str = Field(description="Message to display to the user")
    mcp_server_id: str | None = Field(
        default=None, description="MCP server ID if elicitation is from MCP"
    )
    tool_name: str | None = Field(
        default=None, description="Name of the tool requesting elicitation"
    )
    json_schema: dict[str, Any] | None = Field(
        default=None,
        validation_alias="schema",
        serialization_alias="schema",
        description="JSON schema for FORM mode elicitation",
    )
    url: AnyUrl | None = Field(default=None, description="URL for URL mode elicitation")
    external_elicitation_id: str | None = Field(
        default=None, description="External elicitation ID for tracking"
    )
    response_content: dict[str, Any] | None = Field(
        default=None, description="Content of the user's response"
    )
    responded_at: datetime | None = Field(
        default=None, description="Timestamp when the elicitation was responded to"
    )
    company_id: str = Field(description="Company ID")
    user_id: str = Field(description="User ID")
    chat_id: str | None = Field(
        default=None, description="Chat ID if associated with a chat"
    )
    message_id: str | None = Field(
        default=None, description="Message ID if associated with a message"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata"
    )
    created_at: datetime = Field(
        description="Timestamp when the elicitation was created"
    )
    updated_at: datetime | None = Field(
        default=None, description="Timestamp when the elicitation was last updated"
    )
    expires_at: datetime | None = Field(
        default=None, description="Timestamp when the elicitation expires"
    )

    @field_serializer("created_at", "updated_at", "expires_at", "responded_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetime to ISO format string."""
        if value is None:
            return None
        return value.isoformat()


class ElicitationResponseResult(BaseModel):
    """
    Response for responding to an elicitation request.
    """

    model_config = model_config

    success: bool = Field(description="Whether the response was successful")
    message: str | None = Field(
        default=None, description="Optional message about the response result"
    )


class ElicitationList(BaseModel):
    """
    Response for getting pending elicitations.
    """

    model_config = model_config

    elicitations: list[Elicitation] = Field(description="List of elicitation requests")


class CreateElicitationParams(BaseModel):
    """
    Parameters for creating an elicitation request.
    """

    model_config = model_config

    mode: ElicitationMode = Field(description="Elicitation mode")
    message: str = Field(description="Message to display to the user")
    tool_name: str = Field(description="Name of the tool requesting elicitation")
    json_schema: dict[str, Any] | None = Field(
        default=None,
        validation_alias="schema",
        serialization_alias="schema",
        description="JSON schema for FORM mode elicitation",
    )
    url: AnyUrl | None = Field(default=None, description="URL for URL mode elicitation")
    external_elicitation_id: str | None = Field(
        default=None, description="External elicitation ID for tracking"
    )
    chat_id: str | None = Field(
        default=None, description="Chat ID if associated with a chat"
    )
    message_id: str | None = Field(
        default=None, description="Message ID if associated with a message"
    )
    expires_in_seconds: int | None = Field(
        default=None, description="Expiration time in seconds"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata"
    )


class RespondToElicitationParams(BaseModel):
    """
    Parameters for responding to an elicitation request.
    """

    model_config = model_config

    elicitation_id: str = Field(description="The elicitation ID to respond to")
    action: ElicitationAction = Field(description="Action to take on the elicitation")
    content: dict[str, str | int | bool | list[str]] | None = Field(
        default=None, description="Response content for ACCEPT action"
    )
