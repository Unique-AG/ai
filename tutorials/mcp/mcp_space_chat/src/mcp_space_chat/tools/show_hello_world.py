"""Smoke-test tool: render a dummy Hello World MCP Apps HTML panel."""

from typing import Annotated

from fastmcp.tools import ToolResult, tool
from mcp.types import ContentBlock, TextContent
from pydantic import Field

from mcp_space_chat.ui_resource import (
    HELLO_WORLD_HEIGHT_PX,
    HELLO_WORLD_URI,
    HELLO_WORLD_WIDTH_PX,
    build_legacy_hello_world_resource,
)
from unique_mcp import merge_tool_meta

_TOOL_DESCRIPTION = (
    "Render a dummy Hello World HTML panel (animated, no Unique iframe) to "
    "verify that this MCP host supports MCP Apps / MCP-UI rendering. "
    f"The panel requests a viewport of {HELLO_WORLD_WIDTH_PX}×"
    f"{HELLO_WORLD_HEIGHT_PX} pixels via ui/notifications/size-changed. "
    "Use this before ask_space when debugging missing chat UI."
)

_META = merge_tool_meta(
    {
        "ui": {"resourceUri": HELLO_WORLD_URI},
        # Legacy flat key: some Claude builds only mount the iframe when this
        # deprecated alias is present alongside the nested ui.resourceUri.
        "ui/resourceUri": HELLO_WORLD_URI,
        "unique.app/icon": "sparkles",
        "unique.app/system-prompt": (
            "Choose this tool when the user wants to test whether the MCP "
            "host can display HTML from this server (Hello World smoke test). "
            "After calling it, the animated Hello World panel should appear "
            f"at about {HELLO_WORLD_WIDTH_PX}×{HELLO_WORLD_HEIGHT_PX} px."
        ),
    },
)


@tool(
    name="show_hello_world",
    description=_TOOL_DESCRIPTION,
    meta=_META,
)
async def show_hello_world(
    message: Annotated[
        str | None,
        Field(
            description="Optional text shown in the tool result (not in the HTML).",
        ),
    ] = None,
) -> ToolResult:
    """Return a text ack plus legacy MCP-UI rawHtml; MCP Apps uses the resource."""
    note = message.strip() if message and message.strip() else "Hello World"
    text = (
        f"{note} — MCP Apps panel should render at "
        f"{HELLO_WORLD_WIDTH_PX}×{HELLO_WORLD_HEIGHT_PX} px "
        f"(resource {HELLO_WORLD_URI})."
    )
    content: list[ContentBlock] = [
        TextContent(type="text", text=text),
        build_legacy_hello_world_resource(),
    ]
    return ToolResult(
        content=content,
        structured_content={
            "ok": True,
            "message": note,
            "preferredWidthPx": HELLO_WORLD_WIDTH_PX,
            "preferredHeightPx": HELLO_WORLD_HEIGHT_PX,
            "resourceUri": HELLO_WORLD_URI,
        },
    )
