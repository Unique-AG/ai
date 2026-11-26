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

from unique_sdk._error import APIConnectionError, APIError
from unique_sdk.api_resources._elicitation import Elicitation
from unique_sdk.api_resources._space import Space
from unique_sdk.cli.state import ShellState
from unique_sdk.cli.subagent_turns import (
    TURNS_RELATIVE_DIR,
    record_turn_ended,
    record_turn_started,
)
from unique_sdk.cli.workspace import manifest_path
from unique_sdk.utils.chat_in_space import (
    MessageWaitInterruptedError,
    MessageWaitTimeoutError,
    send_message_and_wait_for_completion,
    wait_for_message_completion,
)
from unique_sdk.utils.subagent_question import (
    SubagentQuestion,
    as_subagent_question,
    find_subagent_question_async,
)

CONFIG_FILENAME = ".unique-subagents.json"
STATE_FILENAME = ".unique-subagent-chats.json"
ENV_CONFIG_PATH = "UNIQUE_SUBAGENTS_CONFIG"
SUBAGENT_ERROR_PREFIX = "subagent:"
SUBAGENT_QUESTION_PREFIX = "subagent-question:"
SUBAGENT_QUESTION_EXIT_CODE = 3


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


def is_question_output(output: str) -> bool:
    """Return ``True`` when the subagent stopped to wait for the user's answer."""
    return output.startswith(SUBAGENT_QUESTION_PREFIX)


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


class _QuestionWatch:
    """Ends a wait when the subagent turn asks the user a question."""

    def __init__(
        self, *, state: ShellState, parent_chat_id: str | None, message_id: str | None
    ) -> None:
        self._state = state
        self._parent_chat_id = parent_chat_id
        self.message_id = message_id
        self.question: SubagentQuestion | None = None

    async def asked(self) -> bool:
        if self._parent_chat_id is None or self.message_id is None:
            return False
        try:
            self.question = await find_subagent_question_async(
                user_id=self._state.config.user_id,
                company_id=self._state.config.company_id,
                parent_chat_id=self._parent_chat_id,
                subagent_message_id=self.message_id,
            )
        except (APIError, APIConnectionError):
            # A failed lookup must not end the wait. The next poll asks again.
            return False
        return self.question is not None


class _WaitSettings(TypedDict):
    poll_interval: float
    max_wait: float
    stop_condition: Literal["stoppedStreamingAt", "completedAt"]


def _wait_settings(subagent: SubagentDefinition) -> _WaitSettings:
    return {
        "poll_interval": _get_float(
            subagent, "pollInterval", "poll_interval", default=1.0
        ),
        "max_wait": _get_float(subagent, "maxWait", "max_wait", default=120.0),
        "stop_condition": _get_stop_condition(subagent),
    }


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
) -> Space.Message | SubagentQuestion:
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
    # Without a correlation the subagent cannot ask in the parent chat.
    watch = _QuestionWatch(
        state=state,
        parent_chat_id=parent_chat_id if correlation else None,
        message_id=None,
    )

    async def _on_message_created(posted: Space.Message) -> None:
        on_turn_created(posted["chatId"], posted["id"])
        watch.message_id = posted["id"]

    try:
        return await send_message_and_wait_for_completion(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            assistant_id=assistant_id,
            text=message,
            tool_choices=_get_forced_tools(subagent),
            chat_id=chat_id,
            correlation=correlation,
            stop_on_abandon=True,
            on_message_created=_on_message_created,
            interrupt=watch.asked,
            **_wait_settings(subagent),
        )
    except MessageWaitInterruptedError:
        assert watch.question is not None
        return watch.question


async def _resume_subagent(
    *,
    state: ShellState,
    subagent: SubagentDefinition,
    question_id: str,
    on_turn_known: Callable[[str, str], None],
) -> Space.Message | SubagentQuestion:
    """Wait again for the subagent turn that asked ``question_id``."""
    _cancel_wait_on_sigterm()
    elicitation = await Elicitation.get_elicitation_async(
        state.config.user_id, state.config.company_id, question_id
    )
    question = as_subagent_question(elicitation)
    if question is None:
        raise ValueError(f"{question_id!r} is not a subagent question")
    on_turn_known(question.subagent_chat_id, question.subagent_message_id)
    if str(elicitation.get("status", "")).upper() == "PENDING":
        return question

    watch = _QuestionWatch(
        state=state,
        parent_chat_id=elicitation.get("chatId"),
        message_id=question.subagent_message_id,
    )
    try:
        return await wait_for_message_completion(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            chat_id=question.subagent_chat_id,
            message_id=question.subagent_message_id,
            stop_on_abandon=True,
            interrupt=watch.asked,
            **_wait_settings(subagent),
        )
    except MessageWaitInterruptedError:
        assert watch.question is not None
        return watch.question


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


def _question_note(
    *, tool_name: str, display_name: str, question: SubagentQuestion
) -> str:
    return "\n".join(
        [
            f"{SUBAGENT_QUESTION_PREFIX} {display_name} is waiting for the "
            "user's answer. It is still running.",
            "",
            "It asked:",
            question.message,
            "",
            "Do this next, in this order:",
            f"1. unique-cli elicit wait {question.elicitation_id}",
            f"2. unique-cli subagent {tool_name} --resume {question.elicitation_id}",
            "",
            "Do not send the task again. Do not answer the question yourself.",
        ]
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
    message: str | None = None,
    *,
    config_path: str | None = None,
    parent_chat_id: str | None = None,
    parent_message_id: str | None = None,
    parent_assistant_id: str | None = None,
    reset_chat: bool = False,
    output_json: bool = False,
    resume_question_id: str | None = None,
) -> str:
    """Invoke one configured connected-space subagent.

    When the subagent asks the user a question, the output starts with
    ``SUBAGENT_QUESTION_PREFIX`` and the subagent turn keeps running. Call
    again with ``resume_question_id`` once the question is answered.
    """
    try:
        if (message is None) == (resume_question_id is None):
            raise ValueError("pass either a message or --resume, not both")
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

        def _on_turn_known(turn_chat_id: str, turn_message_id: str) -> None:
            created.chat_id = turn_chat_id
            created.message_id = turn_message_id

        try:
            if resume_question_id is not None:
                response = asyncio.run(
                    _resume_subagent(
                        state=state,
                        subagent=subagent,
                        question_id=resume_question_id,
                        on_turn_known=_on_turn_known,
                    )
                )
            else:
                assert message is not None
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

        if isinstance(response, SubagentQuestion):
            return _question_note(
                tool_name=tool_name, display_name=display_name, question=response
            )

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
