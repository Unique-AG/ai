"""Send a prompt to a Unique space (sub-agent) and render the live chat."""

import logging
from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.tools import ToolResult, tool
from mcp.types import ContentBlock, TextContent
from pydantic import Field

from mcp_space_chat.auth import resolve_chat_settings, sdk_identity
from mcp_space_chat.embed import build_embed_url
from mcp_space_chat.settings import McpSpaceChatSettings
from mcp_space_chat.ui_resource import CHAT_WINDOW_URI, build_legacy_ui_resource
from unique_mcp import ContextRequirements, MetaKeys, merge_tool_meta
from unique_mcp.unique_injectors import get_unique_settings
from unique_sdk import Space
from unique_toolkit.app.unique_settings import UniqueSettings

_LOGGER = logging.getLogger(__name__)

_TOOL_DESCRIPTION = (
    "Send a prompt to a Unique space (a specialized sub-agent) and open a "
    "live chat window showing the space's answer as it streams in. Returns "
    "immediately with the chat id; the answer is produced asynchronously. "
    "Do NOT call get_space_answer right away — the user already sees the "
    "live chat. Only call get_space_answer later if you need the final text "
    "in your own context (and warn that long tasks may take minutes). "
    "Pass chatId to continue an existing conversation."
)

_META = merge_tool_meta(
    {
        # MCP Apps (SEP-1865): render results with the chat window resource.
        "ui": {"resourceUri": CHAT_WINDOW_URI},
        # Legacy flat key: some Claude builds only mount the iframe when this
        # deprecated alias is present alongside the nested ui.resourceUri.
        "ui/resourceUri": CHAT_WINDOW_URI,
        "unique.app/icon": "message-circle",
        "unique.app/system-prompt": (
            "Choose this tool to delegate a task or question to a space "
            "(sub-agent). Discover space ids with list_spaces first. After "
            "ask_space succeeds, stop and let the user watch the embedded "
            "chat — do not immediately chain get_space_answer."
        ),
    },
    ContextRequirements(required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID]),
)


@tool(
    name="ask_space",
    description=_TOOL_DESCRIPTION,
    meta=_META,
)
async def ask_space(
    space_id: Annotated[
        str,
        Field(
            description="The space (assistant) id, e.g. assistant_… from list_spaces."
        ),
    ],
    prompt: Annotated[
        str,
        Field(description="The prompt or question to send to the space."),
    ],
    chat_id: Annotated[
        str | None,
        Field(
            description=(
                "Existing chat id to continue a conversation. Omit to start a "
                "new chat in the space."
            )
        ),
    ] = None,
    settings: UniqueSettings = Depends(get_unique_settings),
) -> ToolResult:
    """Create a user message in the space and return the chat coordinates.

    The platform runs the space asynchronously; this tool does not wait for
    the answer. The MCP Apps chat window (and legacy MCP-UI iframe) shows the
    real Unique chat embed, which streams the answer and auto-scrolls natively.
    """
    try:
        settings = await resolve_chat_settings(settings)
        user_id, company_id = sdk_identity(settings)
        message = await Space.create_message_async(
            user_id=user_id,
            company_id=company_id,
            assistantId=space_id,
            text=prompt,
            chatId=chat_id,
        )
    except Exception as exc:
        _LOGGER.exception("ask_space error")
        return ToolResult(
            content=[TextContent(type="text", text=str(exc))],
            is_error=True,
        )

    result_chat_id = message.get("chatId") or chat_id or ""
    frontend_base_url = McpSpaceChatSettings().frontend_base_url_str()  # type: ignore[call-arg]
    embed_url = build_embed_url(frontend_base_url, space_id, result_chat_id)
    open_url = f"{frontend_base_url}/chat/{result_chat_id}"

    text = (
        f"Prompt sent to space {space_id} (chatId: {result_chat_id}). "
        "The space is answering asynchronously in the embedded chat window. "
        f"Open directly: {open_url} (embed: {embed_url}). "
        "Do not call get_space_answer unless the user asks you to pull the "
        "final answer text into this conversation."
    )

    content: list[ContentBlock] = [
        TextContent(type="text", text=text),
        build_legacy_ui_resource(embed_url, result_chat_id),
    ]

    return ToolResult(
        content=content,
        structured_content={
            "chatId": result_chat_id,
            "spaceId": space_id,
            "messageId": message.get("id"),
            "embedUrl": embed_url,
            "openUrl": open_url,
        },
    )
