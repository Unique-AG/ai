"""Answers one chat message, calling the space's MCP tools when asked to.

The platform puts the tools it resolved for the space on
`event.payload.mcp_servers`. Each tool has `is_connected`, but that flag
means the chat-service instance that built the event currently holds a live
client for the tool. It is often false for a tool the user can still call,
so this example does not filter on it. An empty list means nothing was
resolved for the turn.

Both entry points share this handler — `app.py` receives events over a
webhook, `sse.py` over the event socket.
"""

import json
import logging
from typing import Any

import unique_sdk
from unique_toolkit import ChatService
from unique_toolkit.app.schemas import ChatEvent, McpServer
from unique_toolkit.app.unique_settings import UniqueContext
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)

logger = logging.getLogger(__name__)

NOT_CONNECTED_MESSAGE = (
    "No MCP tools arrived on this event.\n\n"
    "If the space has MCP tools configured, the chat shows a **Connect** "
    "banner above the message box. Connect there, then send your message "
    "again."
)


def _tool_catalog(mcp_servers: list[McpServer]) -> str:
    """The tools on the event, by server.

    Tool names here are the namespaced `<server>_<tool>` form. That is the name
    `MCP.call_tool` expects, and it differs from the bare name stored on the
    module configuration. `tool.is_connected` is not consulted: it tracks a
    live client on one service instance, not whether the user can call the tool.
    """
    lines: list[str] = []
    for server in mcp_servers:
        lines.append(f"- **{server.name}**")
        for tool in server.tools:
            description = (tool.description or "").strip().splitlines()
            summary = description[0] if description else "no description"
            lines.append(f"    - `{tool.name}` — {summary}")
    return "\n".join(lines)


def _find_tool(mcp_servers: list[McpServer], name: str) -> bool:
    return any(tool.name == name for server in mcp_servers for tool in server.tools)


def _parse_tool_request(text: str) -> tuple[str, dict[str, Any]] | None:
    """Read a `{"name": ..., "arguments": {...}}` message, or return None."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(payload, dict):
        return None

    name = payload.get("name")
    if not isinstance(name, str) or not name:
        return None

    arguments = payload.get("arguments", {})
    if not isinstance(arguments, dict):
        return None

    return name, arguments


def _result_text(response: unique_sdk.MCP) -> str:
    """The text blocks of a tool result.

    Only `content` is guaranteed on a successful call, and an entry can carry
    an image or a resource instead of text.
    """
    blocks: list[str] = []
    for item in getattr(response, "content", None) or []:
        if item.get("type") == "text" and item.get("text"):
            blocks.append(str(item["text"]))
        else:
            blocks.append(f"[{item.get('type', 'unknown')} content]")
    return "\n\n".join(blocks) or "The tool returned no content."


def _call_tool(event: ChatEvent, name: str, arguments: dict[str, Any]) -> str:
    """Call one tool and return the text to show the user.

    A raised call leaves the assistant message spinning, because the webhook
    runs the handler in the background and the event socket only logs the
    error. Say what happened instead, the same way an empty tool list does.
    """
    try:
        response = unique_sdk.MCP.call_tool(
            user_id=event.user_id,
            company_id=event.company_id,
            name=name,
            chatId=event.payload.chat_id,
            messageId=event.payload.assistant_message.id,
            arguments=arguments,
        )
    except Exception:
        logger.exception("MCP call %s failed", name)
        return (
            f"`{name}` could not be called.\n\n"
            "If the server is not connected, use the **Connect** banner "
            "above the message box and send the request again."
        )

    body = _result_text(response)
    if getattr(response, "isError", False):
        return f"`{name}` failed.\n\n{body}"
    return f"`{name}` returned:\n\n{body}"


def handle_event(event: ChatEvent) -> int:
    """Answer one user message, calling an MCP tool when asked to."""
    chat_service = ChatService.from_context(UniqueContext.from_chat_event(event))
    mcp_servers = event.payload.mcp_servers

    logger.info(
        "Module %s: %d MCP server(s) on the event", event.payload.name, len(mcp_servers)
    )

    if not mcp_servers:
        chat_service.modify_assistant_message(
            content=NOT_CONNECTED_MESSAGE, set_completed_at=True
        )
        return 0

    user_text = event.payload.user_message.text
    requested = _parse_tool_request(user_text)

    if requested is not None:
        name, arguments = requested
        if _find_tool(mcp_servers, name):
            chat_service.modify_assistant_message(
                content=_call_tool(event, name, arguments), set_completed_at=True
            )
            return 0

        chat_service.modify_assistant_message(
            content=(
                f"`{name}` is not one of the tools on this event.\n\n"
                f"{_tool_catalog(mcp_servers)}"
            ),
            set_completed_at=True,
        )
        return 0

    # No tool call requested: answer with the configured model and show what is
    # wired up, so the example is useful without a live Atlassian or GitHub call.
    catalog = _tool_catalog(mcp_servers)
    model_name = event.payload.configuration.get("languageModel")
    if not isinstance(model_name, str) or not model_name:
        chat_service.modify_assistant_message(
            content=(
                "This module has no `languageModel` in its configuration.\n\n"
                "Set it to a model registered for your company, then send "
                "your message again."
            ),
            set_completed_at=True,
        )
        return 0

    messages = (
        OpenAIMessageBuilder()
        .system_message_append(
            content=(
                "You are a helpful assistant in a space with MCP tools. You "
                "cannot call them yourself in this example. These tools arrived "
                f"on this event:\n{catalog}"
            )
        )
        .user_message_append(content=user_text)
        .messages
    )

    chat_service.complete_with_references(
        messages=messages,
        model_name=model_name,
        start_text=(
            f"Model `{model_name}`. MCP tools on this event:\n\n{catalog}\n\n"
            'Send `{"name": "<tool>", "arguments": {}}` to call one.\n\n---\n\n'
        ),
    )
    return 0
