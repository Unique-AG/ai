"""Non-blocking peek at a space chat's message history.

Used by the MCP Apps chat window as a polling fallback on hosts (like
claude.ai) whose sandbox CSP blocks nested iframes: the view calls this tool
via host-mediated ``tools/call`` and renders the conversation itself.
"""

from __future__ import annotations

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
    "Return the recent message history of a space chat immediately "
    "(no waiting). Meant for the embedded chat window to poll while an "
    "answer streams. Prefer get_space_answer when you need the final "
    "answer text."
)

_META = merge_tool_meta(
    {
        # App-initiated tool: primarily called by the chat window view.
        "ui": {"visibility": ["app", "model"]},
        "unique.app/icon": "eye",
        "unique.app/system-prompt": (
            "Prefer get_space_answer for reading final answers; this tool "
            "returns the current chat history and may include a partial "
            "streaming assistant message."
        ),
    },
    ContextRequirements(required=[MetaKeys.USER_ID, MetaKeys.COMPANY_ID]),
)

_HISTORY_TAKE = 50


def _serialize_reference(ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": ref.get("name") or "",
        "url": ref.get("url"),
        "sequenceNumber": ref.get("sequenceNumber"),
        "description": ref.get("description"),
        "sourceId": ref.get("sourceId"),
        "source": ref.get("source"),
    }


def _serialize_log_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": event.get("type") or "",
        "text": event.get("text") or "",
        "status": event.get("status"),
    }


def _serialize_message_log(log: dict[str, Any]) -> dict[str, Any]:
    details = log.get("details") or {}
    raw_events = details.get("data") if isinstance(details, dict) else None
    events = [
        _serialize_log_event(e) for e in raw_events or [] if isinstance(e, dict)
    ]
    return {
        "text": log.get("text") or "",
        "status": log.get("status") or "",
        "order": log.get("order") or 0,
        "events": events,
    }


def _extract_message_logs(message: dict[str, Any]) -> list[dict[str, Any]]:
    """Return serialized step logs if the API includes them on the message.

    The public Space message schema does not document message logs, but the
    backend may include them (``messageLogs`` / ``logs``). Pass them through
    so the chat panel can render the Unique steps timeline.
    """
    raw = message.get("messageLogs") or message.get("logs") or []
    if not isinstance(raw, list):
        return []
    logs = [_serialize_message_log(entry) for entry in raw if isinstance(entry, dict)]
    logs.sort(key=lambda entry: entry["order"])
    return logs


def _serialize_message(message: dict[str, Any]) -> dict[str, Any]:
    role = message.get("role") or ""
    stopped = message.get("stoppedStreamingAt")
    # USER/SYSTEM messages are always "done"; ASSISTANT is done once streaming
    # has stopped (or never started and completedAt is set).
    if role == "ASSISTANT":
        done = stopped is not None or (
            message.get("startedStreamingAt") is None
            and message.get("completedAt") is not None
        )
    else:
        done = True
    refs = message.get("references") or []
    return {
        "id": message.get("id"),
        "role": role,
        "text": message.get("text") or "",
        "createdAt": message.get("createdAt"),
        "done": done,
        "references": [_serialize_reference(r) for r in refs if isinstance(r, dict)],
        "logs": _extract_message_logs(message),
    }


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
    """Fetch recent chat messages once and report streaming state."""
    try:
        settings = await resolve_chat_settings(settings)
        user_id, company_id = sdk_identity(settings)
        history = await Space.get_chat_messages_async(
            user_id,
            company_id,
            chat_id,
            take=_HISTORY_TAKE,
        )
    except Exception as exc:
        _LOGGER.exception("peek_space_answer error")
        return ToolResult(
            content=[TextContent(type="text", text=str(exc))],
            is_error=True,
        )

    raw_messages = [m for m in history.get("messages") or [] if isinstance(m, dict)]
    # Present oldest-first for the UI regardless of API ordering. Sort by
    # createdAt (ISO-8601 strings compare chronologically); missing dates
    # keep their relative position at the start.
    ordered = sorted(raw_messages, key=lambda m: m.get("createdAt") or "")
    messages = [_serialize_message(m) for m in ordered]

    # Skip SYSTEM noise for the overall done/latest-text helpers.
    non_system = [m for m in messages if m.get("role") != "SYSTEM"]
    latest = non_system[-1] if non_system else None
    latest_assistant = next(
        (m for m in reversed(non_system) if m.get("role") == "ASSISTANT"),
        None,
    )
    done = bool(
        latest_assistant is not None
        and latest_assistant.get("done")
        and (latest is None or latest.get("role") != "USER")
    )
    text = (latest_assistant or {}).get("text") or ""

    return ToolResult(
        content=[
            TextContent(
                type="text",
                text=text if text else "(no assistant text yet)",
            )
        ],
        structured_content={
            "chatId": chat_id,
            "messages": messages,
            "totalCount": history.get("totalCount", len(messages)),
            "done": done,
            # Back-compat fields for older panel builds / simple callers.
            "messageId": (latest_assistant or {}).get("id"),
            "role": (latest_assistant or {}).get("role") or "",
            "text": text,
            "references": (latest_assistant or {}).get("references") or [],
        },
    )
