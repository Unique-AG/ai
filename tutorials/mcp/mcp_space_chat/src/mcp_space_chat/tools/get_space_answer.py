"""Poll a space chat until the assistant answer is complete and return it."""

import asyncio
import logging
from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.tools import ToolResult, tool
from mcp.types import TextContent
from pydantic import Field

from mcp_space_chat.auth import resolve_chat_settings, sdk_identity
from mcp_space_chat.embed import build_embed_url
from mcp_space_chat.settings import McpSpaceChatSettings
from unique_mcp import ContextRequirements, MetaKeys, merge_tool_meta
from unique_mcp.unique_injectors import get_unique_settings
from unique_sdk import Space
from unique_toolkit.app.unique_settings import UniqueSettings

_LOGGER = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 1.0

_TOOL_DESCRIPTION = (
    "Wait for a space (sub-agent) chat to finish answering and return the "
    "assistant's final answer text. Use the chatId returned by ask_space. "
    "The user already sees the answer streaming in the embedded chat window; "
    "this tool only brings the answer into the model context. Prefer not to "
    "call this immediately after ask_space — especially for long-running "
    "space work (slides, reports); it can block for up to max_wait seconds."
)

_META = merge_tool_meta(
    {
        "unique.app/icon": "message-square-text",
        "unique.app/system-prompt": (
            "Only choose this tool when you need the sub-agent's final text "
            "in your own context. Do not call it immediately after ask_space; "
            "the embedded chat already shows the live answer."
        ),
    },
    ContextRequirements(required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID]),
)


@tool(
    name="get_space_answer",
    description=_TOOL_DESCRIPTION,
    meta=_META,
)
async def get_space_answer(
    chat_id: Annotated[
        str,
        Field(description="The chat id returned by ask_space."),
    ],
    space_id: Annotated[
        str | None,
        Field(
            description=(
                "Optional space id from ask_space; used to keep the embedded "
                "chat window pointed at the same conversation."
            )
        ),
    ] = None,
    max_wait: Annotated[
        float,
        Field(description="Maximum seconds to wait for the answer.", gt=0, le=600),
    ] = 120.0,
    settings: UniqueSettings = Depends(get_unique_settings),
) -> ToolResult:
    """Poll ``Space.get_latest_message`` until the assistant stops streaming.

    Mirrors ``unique_sdk.utils.chat_in_space.send_message_and_wait_for_completion``
    but for a message that was already created (by ask_space), so no new user
    message is sent.
    """
    try:
        settings = await resolve_chat_settings(settings)
        user_id, company_id = sdk_identity(settings)

        answer: Space.Message | None = None
        max_attempts = max(1, int(max_wait // _POLL_INTERVAL_SECONDS))
        for _ in range(max_attempts):
            latest = await Space.get_latest_message_async(user_id, company_id, chat_id)
            if (
                latest.get("role") == "ASSISTANT"
                and latest.get("stoppedStreamingAt") is not None
            ):
                answer = latest
                break
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    except Exception as exc:
        _LOGGER.exception("get_space_answer error")
        return ToolResult(
            content=[TextContent(type="text", text=str(exc))],
            is_error=True,
        )

    if answer is None:
        return ToolResult(
            content=[
                TextContent(
                    type="text",
                    text=(
                        f"The space did not finish answering within {max_wait:.0f}s. "
                        "The chat may still be running; retry with a longer max_wait."
                    ),
                )
            ],
            is_error=True,
        )

    text = answer.get("text") or ""
    references = answer.get("references") or []

    structured: dict = {
        "chatId": chat_id,
        "messageId": answer.get("id"),
        "text": text,
        "references": references,
    }
    if space_id:
        frontend_base_url = McpSpaceChatSettings().frontend_base_url_str()  # type: ignore[call-arg]
        structured["spaceId"] = space_id
        structured["embedUrl"] = build_embed_url(
            frontend_base_url, space_id, chat_id
        )
        structured["openUrl"] = f"{frontend_base_url}/chat/{chat_id}"

    return ToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=structured,
    )
