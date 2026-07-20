"""Non-blocking peek at the latest message of a space chat.

Used by the MCP Apps chat window as a polling fallback on hosts (like
claude.ai) whose sandbox CSP blocks nested iframes: the view calls this tool
via host-mediated ``tools/call`` and renders the streaming answer itself.
"""

import logging
from typing import Annotated

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
    "Return the latest message of a space chat immediately (no waiting). "
    "Meant for the embedded chat window to poll while an answer streams. "
    "Prefer get_space_answer when you need the final answer text."
)

_META = merge_tool_meta(
    {
        # App-initiated tool: primarily called by the chat window view.
        "ui": {"visibility": ["app", "model"]},
        "unique.app/icon": "eye",
        "unique.app/system-prompt": (
            "Prefer get_space_answer for reading final answers; this tool "
            "returns whatever is currently streaming and may be partial."
        ),
    },
    ContextRequirements(required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID]),
)


@tool(
    name="peek_space_answer",
    description=_TOOL_DESCRIPTION,
    meta=_META,
)
async def peek_space_answer(
    chat_id: Annotated[
        str,
        Field(description="The chat id returned by ask_space."),
    ],
    settings: UniqueSettings = Depends(get_unique_settings),
) -> ToolResult:
    """Fetch the latest chat message once and report its streaming state."""
    try:
        settings = await resolve_chat_settings(settings)
        user_id, company_id = sdk_identity(settings)
        latest = await Space.get_latest_message_async(user_id, company_id, chat_id)
    except Exception as exc:
        _LOGGER.exception("peek_space_answer error")
        return ToolResult(
            content=[TextContent(type="text", text=str(exc))],
            is_error=True,
        )

    role = latest.get("role") or ""
    text = latest.get("text") or ""
    done = bool(
        role == "ASSISTANT" and latest.get("stoppedStreamingAt") is not None
    )

    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=text if text else "(no assistant text yet)",
            )
        ],
        structured_content={
            "chatId": chat_id,
            "messageId": latest.get("id"),
            "role": role,
            "text": text,
            "done": done,
            "references": latest.get("references") or [],
        },
    )
