"""Tests for the unique-cli subagent command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from unique_sdk.cli.cli import main as cli_main
from unique_sdk.cli.commands.subagent import cmd_subagent
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState


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
