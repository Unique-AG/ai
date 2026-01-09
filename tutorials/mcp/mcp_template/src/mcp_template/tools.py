from typing import Annotated

from fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import Field

from unique_mcp.provider import BaseProvider
from unique_toolkit.app.unique_settings import UniqueAuth, UniqueSettings


class TemplateTools(BaseProvider):
    """
    Template tools provider. Extend this class to add your custom tools.
    """

    def __init__(self, unique_settings: UniqueSettings | None = None) -> None:
        super().__init__()
        self._unique_settings = (
            unique_settings or UniqueSettings.from_env_auto_with_sdk_init()
        )

    def register(self, *, mcp: FastMCP) -> None:
        """
        Register all tools with the MCP server.
        Add your custom tools here using the @mcp.tool decorator.
        """

        @mcp.tool(
            name="example_tool",
            description="An example tool that demonstrates the pattern",
            meta={
                "unique.app/icon": "tool",
                "unique.app/system-prompt": "Use this tool for example purposes",
            },
            exclude_args=["unique_auth"],
        )
        def _example_tool(
            message: Annotated[
                str,
                Field(description="An example message parameter"),
            ],
            unique_auth: UniqueAuth | None = None,
        ) -> CallToolResult:
            """
            Example tool implementation.
            Replace this with your actual tool logic.
            """

            # Add your tool logic here
            result_text = f"Example tool received: {message}"

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=result_text,
                    )
                ],
            )
