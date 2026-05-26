"""Subagent command: invoke configured connected spaces via the Unique platform."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from unique_sdk._error import APIError
from unique_sdk.api_resources._space import Space
from unique_sdk.cli.state import ShellState
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion

CONFIG_FILENAME = ".unique-subagents.json"
STATE_FILENAME = ".unique-subagent-chats.json"
ENV_CONFIG_PATH = "UNIQUE_SUBAGENTS_CONFIG"
SUBAGENT_ERROR_PREFIX = "subagent:"


class SubagentDefinition(TypedDict, total=False):
    name: str
    displayName: str
    configuration: dict[str, Any]
    assistantId: str
    chatId: str | None
    reuseChat: bool
    forcedTools: list[str]
    pollInterval: float
    maxWait: float
    stopCondition: Literal["stoppedStreamingAt", "completedAt"]


def is_error_output(output: str) -> bool:
    """Return ``True`` when ``output`` is a CLI error message."""
    return output.startswith(SUBAGENT_ERROR_PREFIX)


def resolve_config_path(config_path: str | None = None) -> Path:
    """Resolve the subagent config file path."""
    if config_path:
        return Path(config_path).expanduser()
    env_path = os.environ.get(ENV_CONFIG_PATH)
    if env_path:
        return Path(env_path).expanduser()
    return Path.cwd() / CONFIG_FILENAME


def _load_config(config_path: Path) -> list[SubagentDefinition]:
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"config file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"config file is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("config root must be a JSON object")

    subagents = raw.get("subagents")
    if not isinstance(subagents, list):
        raise ValueError('config must contain a "subagents" array')

    validated: list[SubagentDefinition] = []
    for item in subagents:
        if isinstance(item, dict):
            validated.append(cast(SubagentDefinition, cast(object, item)))
    return validated


def _find_subagent(
    subagents: list[SubagentDefinition],
    tool_name: str,
) -> SubagentDefinition:
    for subagent in subagents:
        if subagent.get("name") == tool_name:
            return subagent
    available = sorted(name for subagent in subagents if (name := subagent.get("name")))
    suffix = f" Available: {', '.join(available)}." if available else ""
    raise ValueError(f"unknown subagent tool {tool_name!r}.{suffix}")


def _get_str(
    subagent: SubagentDefinition,
    *keys: str,
    required: bool = False,
) -> str | None:
    value = _get_value(subagent, *keys)
    if isinstance(value, str) and value.strip():
        return value
    if required:
        key_list = " / ".join(keys)
        raise ValueError(f"subagent {subagent.get('name')!r} is missing {key_list}")
    return None


def _get_value(subagent: SubagentDefinition, *keys: str) -> Any:
    subagent_data = cast(dict[str, Any], cast(object, subagent))
    for key in keys:
        if key in subagent_data:
            return subagent_data[key]
    configuration = subagent.get("configuration")
    if isinstance(configuration, dict):
        for key in keys:
            if key in configuration:
                return configuration[key]
    return None


def _get_bool(
    subagent: SubagentDefinition,
    *keys: str,
    default: bool,
) -> bool:
    value = _get_value(subagent, *keys)
    return value if isinstance(value, bool) else default


def _get_float(
    subagent: SubagentDefinition,
    *keys: str,
    default: float,
) -> float:
    value = _get_value(subagent, *keys)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return default


def _get_forced_tools(subagent: SubagentDefinition) -> list[str] | None:
    value = _get_value(subagent, "forcedTools", "forced_tools")
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value or None
    return None


def _get_stop_condition(
    subagent: SubagentDefinition,
) -> Literal["stoppedStreamingAt", "completedAt"]:
    value = _get_value(subagent, "stopCondition", "stop_condition")
    if value in ("stoppedStreamingAt", "completedAt"):
        return value
    return "completedAt"


def _load_chat_state(state_path: Path) -> dict[str, str]:
    if not state_path.is_file():
        return {}
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        key: value
        for key, value in raw.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def _save_chat_state(state_path: Path, state: dict[str, str]) -> None:
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _format_response(
    *,
    tool_name: str,
    display_name: str,
    response: Space.Message,
    output_json: bool,
) -> str:
    if output_json:
        return json.dumps(response, indent=2, default=str)

    text = response.get("text")
    if text is None:
        raise ValueError(f"subagent {tool_name!r} returned no text")

    lines = [f"Subagent: {display_name} ({tool_name})"]
    chat_id = response.get("chatId")
    if chat_id:
        lines.append(f"Chat: {chat_id}")
    lines.append("")
    lines.append(text)
    return "\n".join(lines)


async def _send_to_subagent(
    *,
    state: ShellState,
    subagent: SubagentDefinition,
    message: str,
    chat_id: str | None,
    parent_chat_id: str | None,
    parent_message_id: str | None,
    parent_assistant_id: str | None,
) -> Space.Message:
    assistant_id = _get_str(
        subagent,
        "assistantId",
        "assistant_id",
        required=True,
    )
    assert assistant_id is not None

    correlation: Space.Correlation | None = None
    if parent_chat_id and parent_message_id and parent_assistant_id:
        correlation = {
            "parentMessageId": parent_message_id,
            "parentChatId": parent_chat_id,
            "parentAssistantId": parent_assistant_id,
        }

    return await send_message_and_wait_for_completion(
        user_id=state.config.user_id,
        company_id=state.config.company_id,
        assistant_id=assistant_id,
        text=message,
        tool_choices=_get_forced_tools(subagent),
        chat_id=chat_id,
        poll_interval=_get_float(
            subagent,
            "pollInterval",
            "poll_interval",
            default=1.0,
        ),
        max_wait=_get_float(
            subagent,
            "maxWait",
            "max_wait",
            default=120.0,
        ),
        stop_condition=_get_stop_condition(subagent),
        correlation=correlation,
    )


def cmd_subagent(
    state: ShellState,
    tool_name: str,
    message: str,
    *,
    config_path: str | None = None,
    parent_chat_id: str | None = None,
    parent_message_id: str | None = None,
    parent_assistant_id: str | None = None,
    reset_chat: bool = False,
    output_json: bool = False,
) -> str:
    """Invoke one configured connected-space subagent."""
    try:
        resolved_config_path = resolve_config_path(config_path)
        subagent = _find_subagent(
            _load_config(resolved_config_path),
            tool_name=tool_name,
        )
        display_name = _get_str(subagent, "displayName") or tool_name
        configured_chat_id = _get_str(subagent, "chatId", "chat_id")
        reuse_chat = _get_bool(subagent, "reuseChat", "reuse_chat", default=True)

        state_path = resolved_config_path.parent / STATE_FILENAME
        chat_id = configured_chat_id
        chat_state: dict[str, str] = {}
        if chat_id is None and reuse_chat and not reset_chat:
            chat_state = _load_chat_state(state_path)
            chat_id = chat_state.get(tool_name)

        response = asyncio.run(
            _send_to_subagent(
                state=state,
                subagent=subagent,
                message=message,
                chat_id=chat_id,
                parent_chat_id=parent_chat_id,
                parent_message_id=parent_message_id,
                parent_assistant_id=parent_assistant_id,
            )
        )

        response_chat_id = response.get("chatId")
        if configured_chat_id is None and reuse_chat and response_chat_id:
            chat_state = chat_state or _load_chat_state(state_path)
            chat_state[tool_name] = response_chat_id
            try:
                _save_chat_state(state_path, chat_state)
            except OSError:
                pass

        return _format_response(
            tool_name=tool_name,
            display_name=display_name,
            response=response,
            output_json=output_json,
        )
    except (ValueError, OSError, TimeoutError, APIError) as exc:
        return f"{SUBAGENT_ERROR_PREFIX} {exc}"
