"""An external module that calls the MCP tools configured on its space.

The platform decides which MCP servers belong to the space (see
`module_configuration.example.json`) and which of them the current user has
authenticated. This module only consumes the result: every server that is
connected for this user arrives on `event.payload.mcp_servers`.
"""

import json
import logging
from typing import Any

from unique_toolkit import ChatService
from unique_toolkit.app.fast_api_factory import build_unique_custom_app
from unique_toolkit.app.schemas import ChatEvent, EventName, McpServer
from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)

import unique_sdk

logger = logging.getLogger(__name__)

NOT_CONNECTED_MESSAGE = (
    "No MCP server is connected for you yet.\n\n"
    "The space has MCP tools configured, so the chat shows a **Connect** "
    "banner above the message box. Connect there, then send your message "
    "again."
)


def _tool_catalog(mcp_servers: list[McpServer]) -> str:
    """The connected tools, by server.

    Tool names here are the namespaced `<server>_<tool>` form. That is the name
    `MCP.call_tool` expects, and it differs from the bare name stored on the
    module configuration.
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
    response = unique_sdk.MCP.call_tool(
        user_id=event.user_id,
        company_id=event.company_id,
        name=name,
        chatId=event.payload.chat_id,
        messageId=event.payload.assistant_message.id,
        arguments=arguments,
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
        "Module %s: %d connected MCP server(s)", event.payload.name, len(mcp_servers)
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
                f"`{name}` is not one of the connected tools.\n\n"
                f"{_tool_catalog(mcp_servers)}"
            ),
            set_completed_at=True,
        )
        return 0

    # No tool call requested: answer with the configured model and show what is
    # wired up, so the example is useful without a live Atlassian or GitHub call.
    catalog = _tool_catalog(mcp_servers)
    model_name = event.payload.configuration["languageModel"]

    messages = (
        OpenAIMessageBuilder()
        .system_message_append(
            content=(
                "You are a helpful assistant in a space with MCP tools. You "
                "cannot call them yourself in this example. These tools are "
                f"connected for this user:\n{catalog}"
            )
        )
        .user_message_append(content=user_text)
        .messages
    )

    chat_service.complete_with_references(
        messages=messages,
        model_name=model_name,
        start_text=(
            f"Model `{model_name}`. Connected MCP tools:\n\n{catalog}\n\n"
            'Send `{"name": "<tool>", "arguments": {}}` to call one.\n\n---\n\n'
        ),
    )
    return 0


# Module level so uvicorn can import it. `unique.env` is looked up in the
# working directory, so run this from the example root.
_SETTINGS = UniqueSettings.from_env_auto_with_sdk_init()

app = build_unique_custom_app(
    title="MCP Custom Module Example",
    settings=_SETTINGS,
    event_handler=handle_event,
    event_constructor=ChatEvent,
    subscribed_event_names=[EventName.EXTERNAL_MODULE_CHOSEN],
)


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run("mcp_custom_module.app:app", host="0.0.0.0", port=5001, reload=True)
