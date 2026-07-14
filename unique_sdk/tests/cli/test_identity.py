"""Tests for unique_sdk.cli.identity turn-identity resolution (UN-22947)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from unique_sdk.cli.cli import main
from unique_sdk.cli.identity import (
    TURN_IDENTITY_ENV_VAR,
    TurnIdentity,
    TurnIdentityError,
    read_turn_identity,
    resolve_message_id,
)


def _write_identity(path: Path, *, message_id: str = "msg-live") -> Path:
    path.write_text(
        json.dumps(
            {
                "message_id": message_id,
                "chat_id": "chat-1",
                "user_id": "u1",
                "company_id": "c1",
                "assistant_id": "a1",
                "turn": 2,
            }
        ),
        encoding="utf-8",
    )
    return path


class TestReadTurnIdentity:
    def test_returns_typed_identity_ignoring_extra_keys(self, tmp_path: Path) -> None:
        path = _write_identity(tmp_path / "turn-identity.json")
        identity = read_turn_identity(path)
        assert identity == TurnIdentity(message_id="msg-live")

    def test_returns_none_when_unconfigured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(TURN_IDENTITY_ENV_VAR, raising=False)
        assert read_turn_identity() is None

    def test_minimal_file_with_only_message_id(self, tmp_path: Path) -> None:
        path = tmp_path / "turn-identity.json"
        path.write_text(json.dumps({"message_id": "msg-1"}), encoding="utf-8")
        identity = read_turn_identity(path)
        assert identity == TurnIdentity(message_id="msg-1")


class TestResolveMessageId:
    def test_explicit_wins_over_file_and_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        identity = _write_identity(tmp_path / "turn-identity.json")
        monkeypatch.setenv(TURN_IDENTITY_ENV_VAR, str(identity))
        monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg-env")
        assert resolve_message_id("msg-explicit") == "msg-explicit"

    def test_file_wins_over_stale_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        identity = _write_identity(
            tmp_path / "turn-identity.json", message_id="msg-file"
        )
        monkeypatch.setenv(TURN_IDENTITY_ENV_VAR, str(identity))
        monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg-stale")
        assert resolve_message_id(None) == "msg-file"

    def test_env_fallback_when_no_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(TURN_IDENTITY_ENV_VAR, raising=False)
        monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg-env")
        assert resolve_message_id(None) == "msg-env"

    def test_missing_file_fails_loud(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing = tmp_path / "missing.json"
        monkeypatch.setenv(TURN_IDENTITY_ENV_VAR, str(missing))
        monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg-stale")
        with pytest.raises(TurnIdentityError, match="missing"):
            resolve_message_id(None)

    def test_malformed_file_fails_loud(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bad = tmp_path / "turn-identity.json"
        bad.write_text("{not-json", encoding="utf-8")
        monkeypatch.setenv(TURN_IDENTITY_ENV_VAR, str(bad))
        with pytest.raises(TurnIdentityError, match="failed to read"):
            resolve_message_id(None)

    def test_missing_message_id_field_fails_loud(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bad = tmp_path / "turn-identity.json"
        bad.write_text(json.dumps({"chat_id": "c1"}), encoding="utf-8")
        monkeypatch.setenv(TURN_IDENTITY_ENV_VAR, str(bad))
        with pytest.raises(TurnIdentityError, match="message_id"):
            resolve_message_id(None)


@patch("unique_sdk.cli.cli.cmd_mcp")
def test_mcp_cli_passes_resolved_message_id(
    mock_cmd_mcp: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_cmd_mcp.return_value = "ok"
    identity = _write_identity(
        tmp_path / "turn-identity.json", message_id="msg-from-file"
    )
    monkeypatch.setenv(TURN_IDENTITY_ENV_VAR, str(identity))
    monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg-stale")
    monkeypatch.setenv("UNIQUE_USER_ID", "u1")
    monkeypatch.setenv("UNIQUE_COMPANY_ID", "c1")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["mcp", "-c", "chat_1", '{"name": "tool", "arguments": {}}'],
    )
    assert result.exit_code == 0
    assert mock_cmd_mcp.call_args.kwargs["message_id"] == "msg-from-file"


@patch("unique_sdk.cli.cli.cmd_mcp")
def test_mcp_cli_fails_when_turn_identity_file_missing(
    mock_cmd_mcp: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(TURN_IDENTITY_ENV_VAR, str(tmp_path / "gone.json"))
    monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg-stale")
    monkeypatch.setenv("UNIQUE_USER_ID", "u1")
    monkeypatch.setenv("UNIQUE_COMPANY_ID", "c1")

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["mcp", "-c", "chat_1", '{"name": "tool", "arguments": {}}'],
    )
    assert result.exit_code == 2
    assert "Error" in result.output
    mock_cmd_mcp.assert_not_called()
