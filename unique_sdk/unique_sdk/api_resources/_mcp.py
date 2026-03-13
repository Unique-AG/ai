from typing import (
    Any,
    Literal,
    TypedDict,
    Unpack,
    cast,
)

from typing_extensions import NotRequired

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class CallToolTextResourceDto(TypedDict):
    """Text resource containing URI, optional MIME type, and text content."""

    uri: str
    mimeType: str | None
    text: str


class CallToolBlobResourceDto(TypedDict):
    """Blob resource containing URI, optional MIME type, and base64-encoded content."""

    uri: str
    mimeType: str | None
    blob: str


class CallToolContentDto(TypedDict):
    """Content returned by an MCP tool call."""

    type: Literal["text", "image", "audio", "resource_link", "resource"]

    # Optional fields for different content types
    text: NotRequired[str | None]  # For type: "text"
    data: NotRequired[str | None]  # Base64 data for type: "image" or "audio"
    mimeType: NotRequired[str | None]  # For type: "image", "audio", or "resource_link"
    uri: NotRequired[str | None]  # For type: "resource_link"
    name: NotRequired[str | None]  # For type: "resource_link"
    description: NotRequired[str | None]  # For type: "resource_link"
    resource: NotRequired[
        (CallToolTextResourceDto | CallToolBlobResourceDto) | None
    ]  # For type: "resource"


class MCP(APIResource["MCP"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["mcp.call_tool"]:
        return "mcp.call_tool"

    class CallToolParams(RequestOptions):
        """Parameters for calling an MCP tool."""

        name: str
        messageId: str
        chatId: str
        arguments: dict[str, Any]

    # Response fields
    content: list[CallToolContentDto]
    isError: bool
    mcpServerId: str
    name: str

    @classmethod
    def call_tool(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MCP.CallToolParams"],
    ) -> "MCP":
        """
        Call an MCP tool with the specified name and arguments.

        Args:
            user_id: The ID of the user making the request
            company_id: The ID of the company
            **params: Tool parameters including name and arguments

        Returns:
            MCP: The response from the MCP tool call
        """
        return cast(
            "MCP",
            cls._static_request(
                "post",
                "/mcp/call-tool",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def call_tool_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MCP.CallToolParams"],
    ) -> "MCP":
        """
        Asynchronously call an MCP tool with the specified name and arguments.

        Args:
            user_id: The ID of the user making the request
            company_id: The ID of the company
            **params: Tool parameters including name and arguments

        Returns:
            MCP: The response from the MCP tool call
        """
        return cast(
            "MCP",
            await cls._static_request_async(
                "post",
                "/mcp/call-tool",
                user_id,
                company_id,
                params=params,
            ),
        )
