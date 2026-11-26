"""Tests for the unique-cli subagent command."""

from __future__ import annotations

import json
import os
import signal
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from unique_sdk._error import APIError
from unique_sdk.cli.cli import main as cli_main
from unique_sdk.cli.commands.subagent import cmd_subagent, is_error_output
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState
from unique_sdk.cli.subagent_turns import (
    TURNS_RELATIVE_DIR,
    SubagentTurn,
    read_open_turns,
)
from unique_sdk.utils.chat_in_space import MessageWaitTimeoutError


def _config() -> Config:
    return Config(
        user_id="u1",
        company_id="c1",
        api_key="key",
        app_id="app",
        api_base="https://example.com",
    )


def _state() -> ShellState:
    return ShellState(_config())


def _open_turns(workspace: Path) -> list[SubagentTurn]:
    return read_open_turns(turns_dir=workspace / TURNS_RELATIVE_DIR)


def _child_turn(
    *, parent_chat_id: str | None = None, parent_message_id: str | None = None
) -> SubagentTurn:
    return {
        "version": 1,
        "chatId": "chat-child",
        "messageId": "msg-user",
        "parentChatId": parent_chat_id,
        "parentMessageId": parent_message_id,
    }


def _write_subagents_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "subagents": [
                    {
                        "name": "LegalReview",
                        "displayName": "Legal Review",
                        "assistantId": "assistant-legal",
                        "forcedTools": ["InternalSearch"],
                        "pollInterval": 0.5,
                        "maxWait": 30,
                        "stopCondition": "completedAt",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


@patch(
    "unique_sdk.cli.commands.subagent.send_message_and_wait_for_completion",
    new_callable=AsyncMock,
)
def test_cmd_subagent_sends_message_with_correlation(
    mock_send: AsyncMock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)
    mock_send.return_value = {
        "id": "msg-child",
        "chatId": "chat-child",
        "text": "Reviewed clause.",
        "originalText": None,
        "role": "ASSISTANT",
        "debugInfo": None,
        "gptRequest": None,
        "completedAt": "now",
        "createdAt": "now",
        "updatedAt": "now",
        "startedStreamingAt": "now",
        "stoppedStreamingAt": "now",
        "references": None,
        "assessment": None,
    }

    out = cmd_subagent(
        _state(),
        "LegalReview",
        "Please review this clause",
        config_path=str(config_path),
        parent_chat_id="chat-parent",
        parent_message_id="msg-parent",
        parent_assistant_id="assistant-parent",
    )

    assert "Subagent: Legal Review (LegalReview)" in out
    assert "Reviewed clause." in out
    mock_send.assert_awaited_once()
    kwargs = mock_send.await_args.kwargs
    assert kwargs["user_id"] == "u1"
    assert kwargs["company_id"] == "c1"
    assert kwargs["assistant_id"] == "assistant-legal"
    assert kwargs["text"] == "Please review this clause"
    assert kwargs["tool_choices"] == ["InternalSearch"]
    assert kwargs["poll_interval"] == 0.5
    assert kwargs["max_wait"] == 30.0
    assert kwargs["correlation"] == {
        "parentMessageId": "msg-parent",
        "parentChatId": "chat-parent",
        "parentAssistantId": "assistant-parent",
    }
    saved_state = json.loads((tmp_path / ".unique-subagent-chats.json").read_text())
    assert saved_state == {"LegalReview": "chat-child"}


@patch("unique_sdk.cli.commands.subagent._save_chat_state")
@patch(
    "unique_sdk.cli.commands.subagent.send_message_and_wait_for_completion",
    new_callable=AsyncMock,
)
def test_cmd_subagent_returns_response_when_chat_state_save_fails(
    mock_send: AsyncMock,
    mock_save_chat_state: Mock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)
    mock_send.return_value = {
        "id": "msg-child",
        "chatId": "chat-child",
        "text": "Reviewed clause.",
        "originalText": None,
        "role": "ASSISTANT",
        "debugInfo": None,
        "gptRequest": None,
        "completedAt": "now",
        "createdAt": "now",
        "updatedAt": "now",
        "startedStreamingAt": "now",
        "stoppedStreamingAt": "now",
        "references": None,
        "assessment": None,
    }
    mock_save_chat_state.side_effect = OSError("disk full")

    out = cmd_subagent(
        _state(),
        "LegalReview",
        "Please review this clause",
        config_path=str(config_path),
    )

    assert "Subagent: Legal Review (LegalReview)" in out
    assert "Reviewed clause." in out
    assert not is_error_output(out)


@patch("unique_sdk.cli.commands.subagent._save_chat_state")
@patch(
    "unique_sdk.cli.commands.subagent.send_message_and_wait_for_completion",
    new_callable=AsyncMock,
)
def test_cmd_subagent__early_chat_save_fails__saves_again_after_success(
    mock_send: AsyncMock,
    mock_save_chat_state: Mock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)
    response = {"id": "msg-child", "chatId": "chat-child", "text": "Reviewed."}

    async def _send(**kwargs: Any) -> dict[str, str]:
        await kwargs["on_message_created"](response)
        return response

    mock_send.side_effect = _send
    mock_save_chat_state.side_effect = [OSError("disk full"), None]

    out = cmd_subagent(
        _state(),
        "LegalReview",
        "Please review this clause",
        config_path=str(config_path),
    )

    assert not is_error_output(out)
    assert mock_save_chat_state.call_count == 2
    assert mock_save_chat_state.call_args.args[1] == {"LegalReview": "chat-child"}


def test_cmd_subagent_reports_unknown_tool(tmp_path: Path) -> None:
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)

    out = cmd_subagent(
        _state(),
        "Finance",
        "hello",
        config_path=str(config_path),
    )

    assert out.startswith("subagent: unknown subagent tool 'Finance'")
    assert "LegalReview" in out


def test_subagent_error_output_detector() -> None:
    assert is_error_output("subagent: unknown subagent tool 'Finance'")
    assert not is_error_output("Subagent: Legal Review (LegalReview)")


@patch("unique_sdk.cli.cli.cmd_subagent")
def test_cli_subagent_command_wiring(mock_cmd_subagent: object) -> None:
    mock_cmd_subagent.return_value = "ok"  # type: ignore[attr-defined]
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        [
            "subagent",
            "LegalReview",
            "review this",
            "--config",
            __file__,
            "--reset-chat",
        ],
        env={
            "UNIQUE_USER_ID": "u1",
            "UNIQUE_COMPANY_ID": "c1",
            "UNIQUE_CHAT_ID": "chat-parent",
            "UNIQUE_MESSAGE_ID": "msg-parent",
            "UNIQUE_ASSISTANT_ID": "assistant-parent",
        },
    )

    assert result.exit_code == 0
    assert result.output.strip() == "ok"
    mock_cmd_subagent.assert_called_once()  # type: ignore[attr-defined]
    kwargs = mock_cmd_subagent.call_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["tool_name"] == "LegalReview"
    assert kwargs["message"] == "review this"
    assert kwargs["parent_chat_id"] == "chat-parent"
    assert kwargs["parent_message_id"] == "msg-parent"
    assert kwargs["parent_assistant_id"] == "assistant-parent"
    assert kwargs["reset_chat"] is True


@patch("unique_sdk.cli.cli.cmd_subagent")
def test_cli_subagent_error_exits_non_zero(mock_cmd_subagent: object) -> None:
    mock_cmd_subagent.return_value = "subagent: unknown subagent tool 'Finance'"  # type: ignore[attr-defined]
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        [
            "subagent",
            "Finance",
            "hello",
        ],
        env={
            "UNIQUE_USER_ID": "u1",
            "UNIQUE_COMPANY_ID": "c1",
        },
    )

    assert result.exit_code == 1
    assert result.output.strip() == "subagent: unknown subagent tool 'Finance'"


def _timeout(*, turn_stopped: bool) -> object:
    async def post_then_time_out(**kwargs: object) -> None:
        on_message_created = kwargs["on_message_created"]
        assert callable(on_message_created)
        await on_message_created({"chatId": "chat-child", "id": "msg-user"})
        raise MessageWaitTimeoutError(
            chat_id="chat-child", message_id="msg-user", turn_stopped=turn_stopped
        )

    return post_then_time_out


@pytest.mark.ai
@patch(
    "unique_sdk.cli.commands.subagent.send_message_and_wait_for_completion",
    new_callable=AsyncMock,
)
def test_cmd_subagent__asks_the_wait_to_stop_an_abandoned_turn(
    mock_send: AsyncMock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)
    mock_send.return_value = {"chatId": "chat-child", "text": "ok"}

    _ = cmd_subagent(_state(), "LegalReview", "hi", config_path=str(config_path))

    assert mock_send.await_args.kwargs["stop_on_abandon"] is True


@pytest.mark.ai
@patch(
    "unique_sdk.cli.commands.subagent.send_message_and_wait_for_completion",
    new_callable=AsyncMock,
)
def test_cmd_subagent__timeout_with_stopped_turn__says_stopped_and_keeps_chat(
    mock_send: AsyncMock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)
    mock_send.side_effect = _timeout(turn_stopped=True)

    out = cmd_subagent(_state(), "LegalReview", "hi", config_path=str(config_path))

    assert is_error_output(out)
    assert "Legal Review did not answer in time. Its turn was stopped." in out
    saved = json.loads((tmp_path / ".unique-subagent-chats.json").read_text())
    assert saved == {"LegalReview": "chat-child"}


@pytest.mark.ai
@patch(
    "unique_sdk.cli.commands.subagent.send_message_and_wait_for_completion",
    new_callable=AsyncMock,
)
def test_cmd_subagent__timeout_with_failed_stop__names_the_running_chat(
    mock_send: AsyncMock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)
    mock_send.side_effect = _timeout(turn_stopped=False)

    out = cmd_subagent(_state(), "LegalReview", "hi", config_path=str(config_path))

    assert is_error_output(out)
    assert "still running in chat chat-child" in out


@pytest.mark.ai
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals")
def test_cmd_subagent__sigterm_during_wait__stops_turn_then_exits_143(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIQUE_WORKSPACE_DIR", str(tmp_path))
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)
    stop = AsyncMock()

    async def never_finishes(*_args: object, **_kwargs: object) -> dict[str, object]:
        os.kill(os.getpid(), signal.SIGTERM)
        return {"role": "ASSISTANT", "stoppedStreamingAt": None, "text": None}

    module = "unique_sdk.utils.chat_in_space"
    with (
        patch(
            f"{module}.Space.create_message_async",
            new_callable=AsyncMock,
            return_value={"id": "msg-user", "chatId": "chat-child"},
        ),
        patch(f"{module}.Space.get_latest_message_async", never_finishes),
        patch(f"{module}.Message.stop_async", stop),
        pytest.raises(SystemExit) as raised,
    ):
        _ = cmd_subagent(_state(), "LegalReview", "hi", config_path=str(config_path))

    assert raised.value.code == 128 + signal.SIGTERM
    stop.assert_awaited_once_with("u1", "c1", "msg-user", chatId="chat-child")
    saved = json.loads((tmp_path / ".unique-subagent-chats.json").read_text())
    assert saved == {"LegalReview": "chat-child"}
    out = capsys.readouterr().out
    assert out.startswith("subagent: terminated while waiting for Legal Review.")
    assert "chat chat-child was asked to stop" in out
    # The wait does not report whether its stop succeeded, so the record
    # stays for the host, which skips a turn that is already stopped.
    assert _open_turns(tmp_path) == [_child_turn()]


@pytest.mark.ai
@patch(
    "unique_sdk.cli.commands.subagent.send_message_and_wait_for_completion",
    new_callable=AsyncMock,
)
def test_cmd_subagent__while_waiting__turn_is_recorded_in_the_workspace_with_its_parent(
    mock_send: AsyncMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIQUE_WORKSPACE_DIR", str(tmp_path))
    config_dir = tmp_path / "elsewhere"
    config_dir.mkdir()
    config_path = config_dir / "subagents.json"
    _write_subagents_config(config_path)
    open_during_wait: list[SubagentTurn] = []

    async def _send(**kwargs: Any) -> dict[str, str]:
        await kwargs["on_message_created"]({"chatId": "chat-child", "id": "msg-user"})
        open_during_wait.extend(_open_turns(tmp_path))
        return {"id": "msg-answer", "chatId": "chat-child", "text": "Reviewed."}

    mock_send.side_effect = _send

    out = cmd_subagent(
        _state(),
        "LegalReview",
        "hi",
        config_path=str(config_path),
        parent_chat_id="chat-parent",
        parent_message_id="msg-parent",
        parent_assistant_id="assistant-parent",
    )

    assert not is_error_output(out)
    assert open_during_wait == [
        _child_turn(parent_chat_id="chat-parent", parent_message_id="msg-parent")
    ]
    assert _open_turns(tmp_path) == []


@pytest.mark.ai
@patch(
    "unique_sdk.cli.commands.subagent.send_message_and_wait_for_completion",
    new_callable=AsyncMock,
)
def test_cmd_subagent__timeout_with_stopped_turn__clears_the_record(
    mock_send: AsyncMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIQUE_WORKSPACE_DIR", str(tmp_path))
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)
    mock_send.side_effect = _timeout(turn_stopped=True)

    _ = cmd_subagent(_state(), "LegalReview", "hi", config_path=str(config_path))

    assert _open_turns(tmp_path) == []


@pytest.mark.ai
@patch(
    "unique_sdk.cli.commands.subagent.send_message_and_wait_for_completion",
    new_callable=AsyncMock,
)
def test_cmd_subagent__timeout_with_failed_stop__keeps_the_record(
    mock_send: AsyncMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIQUE_WORKSPACE_DIR", str(tmp_path))
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)
    mock_send.side_effect = _timeout(turn_stopped=False)

    _ = cmd_subagent(_state(), "LegalReview", "hi", config_path=str(config_path))

    assert _open_turns(tmp_path) == [_child_turn()]


@pytest.mark.ai
@patch(
    "unique_sdk.cli.commands.subagent.send_message_and_wait_for_completion",
    new_callable=AsyncMock,
)
def test_cmd_subagent__wait_fails_with_api_error__keeps_the_record(
    mock_send: AsyncMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UNIQUE_WORKSPACE_DIR", str(tmp_path))
    config_path = tmp_path / ".unique-subagents.json"
    _write_subagents_config(config_path)

    async def _send(**kwargs: Any) -> dict[str, str]:
        await kwargs["on_message_created"]({"chatId": "chat-child", "id": "msg-user"})
        raise APIError("gateway timeout")

    mock_send.side_effect = _send

    out = cmd_subagent(_state(), "LegalReview", "hi", config_path=str(config_path))

    assert is_error_output(out)
    assert _open_turns(tmp_path) == [_child_turn()]
