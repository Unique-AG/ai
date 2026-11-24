"""Subagent command: invoke configured connected spaces via the Unique platform."""

from __future__ import annotations

import asyncio
import json
import os
import signal
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from unique_sdk._error import APIError
from unique_sdk.api_resources._space import Space
from unique_sdk.cli.state import ShellState
from unique_sdk.cli.subagent_turns import (
    TURNS_RELATIVE_DIR,
    record_turn_ended,
    record_turn_started,
)
from unique_sdk.cli.workspace import manifest_path
from unique_sdk.utils.chat_in_space import (
    MessageWaitTimeoutError,
    send_message_and_wait_for_completion,
)

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


@dataclass
class _CreatedTurn:
    chat_id: str | None = None
    message_id: str | None = None


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
    on_turn_created: Callable[[str, str], None],
) -> Space.Message:
    assistant_id = _get_str(
        subagent,
        "assistantId",
        "assistant_id",
        required=True,
    )
    assert assistant_id is not None
    _cancel_wait_on_sigterm()

    correlation: Space.Correlation | None = None
    if parent_chat_id and parent_message_id and parent_assistant_id:
        correlation = {
            "parentMessageId": parent_message_id,
            "parentChatId": parent_chat_id,
            "parentAssistantId": parent_assistant_id,
        }

    async def _on_message_created(posted: Space.Message) -> None:
        on_turn_created(posted["chatId"], posted["id"])

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
        stop_on_abandon=True,
        on_message_created=_on_message_created,
    )


def _cancel_wait_on_sigterm() -> None:
    """Turn SIGTERM into a cancellation, so the wait stops the subagent turn first."""
    task = asyncio.current_task()
    if task is None:
        return
    try:
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    except (NotImplementedError, RuntimeError, ValueError):
        # Windows event loops and non-main threads cannot install signal handlers.
        return


def _remember_chat(
    *,
    state_path: Path,
    chat_state: dict[str, str],
    tool_name: str,
    chat_id: str,
) -> bool:
    chat_state = chat_state or _load_chat_state(state_path)
    chat_state[tool_name] = chat_id
    try:
        _save_chat_state(state_path, chat_state)
    except OSError:
        return False
    return True


def _timeout_note(*, display_name: str, timeout: MessageWaitTimeoutError) -> str:
    if timeout.turn_stopped:
        return f"{display_name} did not answer in time. Its turn was stopped."
    return (
        f"{display_name} did not answer in time and could not be stopped. "
        f"It is still running in chat {timeout.chat_id}. "
        "Do not send the same task again."
    )


def _terminated_note(*, display_name: str, chat_id: str | None) -> str:
    note = f"{SUBAGENT_ERROR_PREFIX} terminated while waiting for {display_name}."
    if chat_id is None:
        return note
    return (
        f"{note} Its turn in chat {chat_id} was asked to stop. "
        "Do not send the same task again before checking that chat."
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

        remembers_chat = configured_chat_id is None and reuse_chat
        turns_dir = manifest_path(TURNS_RELATIVE_DIR)
        created = _CreatedTurn()
        saved_chat_ids: set[str] = set()

        def _on_turn_created(turn_chat_id: str, turn_message_id: str) -> None:
            created.chat_id = turn_chat_id
            created.message_id = turn_message_id
            record_turn_started(
                turns_dir=turns_dir,
                chat_id=turn_chat_id,
                message_id=turn_message_id,
                parent_chat_id=parent_chat_id,
                parent_message_id=parent_message_id,
            )
            if remembers_chat and _remember_chat(
                state_path=state_path,
                chat_state=chat_state,
                tool_name=tool_name,
                chat_id=turn_chat_id,
            ):
                saved_chat_ids.add(turn_chat_id)

        try:
            response = asyncio.run(
                _send_to_subagent(
                    state=state,
                    subagent=subagent,
                    message=message,
                    chat_id=chat_id,
                    parent_chat_id=parent_chat_id,
                    parent_message_id=parent_message_id,
                    parent_assistant_id=parent_assistant_id,
                    on_turn_created=_on_turn_created,
                )
            )
        except MessageWaitTimeoutError as timeout:
            # A turn that could not be stopped keeps its record, so the
            # caller's host can stop it later.
            if timeout.turn_stopped:
                record_turn_ended(turns_dir=turns_dir, message_id=timeout.message_id)
            note = _timeout_note(display_name=display_name, timeout=timeout)
            return f"{SUBAGENT_ERROR_PREFIX} {note}"
        except asyncio.CancelledError:
            # The wait does not report whether its stop succeeded, so the
            # record stays. The host skips a turn that is already stopped.
            print(
                _terminated_note(display_name=display_name, chat_id=created.chat_id),
                flush=True,
            )
            raise SystemExit(128 + signal.SIGTERM) from None

        if created.message_id is not None:
            record_turn_ended(turns_dir=turns_dir, message_id=created.message_id)

        response_chat_id = response.get("chatId")
        if remembers_chat and response_chat_id not in (None, *saved_chat_ids):
            _remember_chat(
                state_path=state_path,
                chat_state=chat_state,
                tool_name=tool_name,
                chat_id=response_chat_id,
            )

        return _format_response(
            tool_name=tool_name,
            display_name=display_name,
            response=response,
            output_json=output_json,
        )
    except (ValueError, OSError, TimeoutError, APIError) as exc:
        return f"{SUBAGENT_ERROR_PREFIX} {exc}"
