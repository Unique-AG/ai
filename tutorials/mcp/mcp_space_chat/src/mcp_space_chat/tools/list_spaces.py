"""List the Unique spaces (assistants) available to the current user."""

import logging
from typing import Annotated, Any

from fastmcp.dependencies import Depends
from fastmcp.tools import ToolResult, tool
from mcp.types import TextContent
from pydantic import Field

from mcp_space_chat.auth import resolve_chat_settings, sdk_identity
from unique_mcp import ContextRequirements, MetaKeys, merge_tool_meta
from unique_mcp.unique_injectors import get_unique_settings
from unique_sdk import Space
from unique_toolkit.app.unique_settings import UniqueSettings

_LOGGER = logging.getLogger(__name__)

_TOOL_DESCRIPTION = (
    "List the Unique spaces (assistants) the current user can chat with. "
    "Each space is a specialized sub-agent. Use the returned space id with "
    "the ask_space tool to send it a prompt."
)

_META = merge_tool_meta(
    {
        "unique.app/icon": "list",
        "unique.app/system-prompt": (
            "Choose this tool to discover which spaces (sub-agents) are "
            "available before calling one with ask_space."
        ),
    },
    ContextRequirements(required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID]),
)


@tool(
    name="list_spaces",
    description=_TOOL_DESCRIPTION,
    meta=_META,
)
async def list_spaces(
    name: Annotated[
        str | None,
        Field(description="Optional case-insensitive partial name filter."),
    ] = None,
    settings: UniqueSettings = Depends(get_unique_settings),
) -> ToolResult:
    """List spaces via ``Space.get_spaces`` for the resolved identity."""
    try:
        settings = await resolve_chat_settings(settings)
        user_id, company_id = sdk_identity(settings)
        result = await Space.get_spaces_async(
            user_id=user_id,
            company_id=company_id,
            name=name,
            take=100,
        )
    except Exception as exc:
        _LOGGER.exception("list_spaces error")
        return ToolResult(
            content=[TextContent(type="text", text=str(exc))],
            is_error=True,
        )

    spaces: list[dict[str, Any]] = [
        {
            "id": space.get("id"),
            "name": space.get("name"),
            "title": space.get("title"),
            "explanation": space.get("explanation"),
        }
        for space in result.get("data", [])
    ]

    if not spaces:
        return ToolResult(
            content=[TextContent(type="text", text="No spaces found.")],
            structured_content={"spaces": []},
        )

    lines = ["Available spaces (sub-agents):"]
    for space in spaces:
        label = space["title"] or space["name"]
        line = f"- {label} (id: {space['id']})"
        if space["explanation"]:
            line += f" — {space['explanation']}"
        lines.append(line)

    return ToolResult(
        content=[TextContent(type="text", text="\n".join(lines))],
        structured_content={"spaces": spaces},
    )
