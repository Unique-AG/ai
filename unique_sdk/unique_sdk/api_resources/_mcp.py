from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    Union,
    Unpack,
    cast,
)

from typing_extensions import NotRequired

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class CallToolTextResourceDto(TypedDict):
    """Text resource containing URI, optional MIME type, and text content."""

    uri: str
    mimeType: Optional[str]
    text: str


class CallToolBlobResourceDto(TypedDict):
    """Blob resource containing URI, optional MIME type, and base64-encoded content."""

    uri: str
    mimeType: Optional[str]
    blob: str


class CallToolContentDto(TypedDict):
    """Content returned by an MCP tool call."""

    type: Literal["text", "image", "audio", "resource_link", "resource"]

    # Optional fields for different content types
    text: NotRequired[Optional[str]]  # For type: "text"
    data: NotRequired[Optional[str]]  # Base64 data for type: "image" or "audio"
    mimeType: NotRequired[
        Optional[str]
    ]  # For type: "image", "audio", or "resource_link"
    uri: NotRequired[Optional[str]]  # For type: "resource_link"
    name: NotRequired[Optional[str]]  # For type: "resource_link"
    description: NotRequired[Optional[str]]  # For type: "resource_link"
    resource: NotRequired[
        Optional[Union[CallToolTextResourceDto, CallToolBlobResourceDto]]
    ]  # For type: "resource"


class MCP(APIResource["MCP"]):
    OBJECT_NAME: ClassVar[Literal["mcp.call_tool"]] = "mcp.call_tool"

    class CallToolParams(RequestOptions):
        """Parameters for calling an MCP tool."""

        name: str
        arguments: Dict[str, Any]

    # Response fields
    content: List[CallToolContentDto]
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
