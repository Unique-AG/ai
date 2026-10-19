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


class McpServerToolDto(TypedDict):
    """A tool of an MCP server that the company has enabled."""

    name: str
    description: str | None


class McpServerDto(TypedDict):
    """An MCP server (connector) of the company that can be attached to a space."""

    id: str
    name: str
    description: str | None
    requiresOAuth: bool
    isSpaceRestricted: bool
    allowedSpaceIds: list[str]
    tools: list[McpServerToolDto]


class McpServersResponse(TypedDict):
    mcpServers: list[McpServerDto]


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

    # Response fields.
    #
    # The MCP spec only guarantees ``content`` on a successful ``CallToolResult``;
    # ``isError``, ``mcpServerId``, and ``name`` are optional in practice (some
    # Unique backend builds omit them on success). Consumers must access these
    # defensively (e.g. via ``getattr(..., default)``) to stay compatible with
    # lean server responses.
    content: list[CallToolContentDto]
    isError: bool | None
    mcpServerId: str | None
    name: str | None

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

    @classmethod
    def list_servers(
        cls,
        user_id: str,
        company_id: str,
    ) -> McpServersResponse:
        """
        List the company's MCP servers that can be attached to a space, with their
        tools. Never returns server URLs or credentials.

        Args:
            user_id: The ID of the user making the request
            company_id: The ID of the company

        Returns:
            McpServersResponse: The servers, sorted by name
        """
        return cast(
            McpServersResponse,
            cls._static_request(
                "get",
                "/mcp/servers",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def list_servers_async(
        cls,
        user_id: str,
        company_id: str,
    ) -> McpServersResponse:
        """
        Asynchronously list the company's MCP servers that can be attached to a space,
        with their tools. Never returns server URLs or credentials.

        Args:
            user_id: The ID of the user making the request
            company_id: The ID of the company

        Returns:
            McpServersResponse: The servers, sorted by name
        """
        return cast(
            McpServersResponse,
            await cls._static_request_async(
                "get",
                "/mcp/servers",
                user_id,
                company_id,
            ),
        )
