"""MCP command: call MCP server tools via the Unique platform."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import format_mcp_response
from unique_sdk.cli.state import ShellState


def _read_payload(
    payload: str | None,
    file: str | None,
    stdin: bool,
) -> str:
    """Resolve the JSON payload from one of the three input sources."""
    sources = sum([payload is not None, file is not None, stdin])
    if sources == 0:
        raise ValueError(
            "No payload provided. Pass a JSON string, use --file, or --stdin."
        )
    if sources > 1:
        raise ValueError(
            "Ambiguous input: provide exactly one of PAYLOAD, --file, or --stdin."
        )

    if stdin:
        return sys.stdin.read()
    if file is not None:
        return Path(file).read_text(encoding="utf-8")
    assert payload is not None
    return payload


def _parse_and_validate(raw: str) -> tuple[str, dict[str, Any]]:
    """Parse JSON and validate the required ``name`` and ``arguments`` fields."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Payload must be a JSON object.")

    if "name" not in data:
        raise ValueError('Missing required field "name" in JSON payload.')

    name: str = data["name"]
    arguments: dict[str, Any] = data.get("arguments", {})

    if not isinstance(arguments, dict):
        raise ValueError('"arguments" must be a JSON object.')

    return name, arguments


def cmd_mcp(
    state: ShellState,
    chat_id: str,
    message_id: str,
    payload: str | None = None,
    file: str | None = None,
    stdin: bool = False,
) -> str:
    """Call an MCP tool with a JSON payload containing name and arguments."""
    try:
        raw = _read_payload(payload, file, stdin)
        name, arguments = _parse_and_validate(raw)

        response = unique_sdk.MCP.call_tool(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            name=name,
            chatId=chat_id,
            messageId=message_id,
            arguments=arguments,
        )

    except (ValueError, OSError, unique_sdk.APIError) as e:
        return f"mcp: {e}"

    try:
        return format_mcp_response(response, tool_name=name)
    except Exception as fmt_exc:
        try:
            fallback = json.dumps(dict(response), indent=2, default=str)
        except Exception:
            fallback = repr(response)
        return f"mcp: formatter error ({fmt_exc}); raw response:\n{fallback}"
