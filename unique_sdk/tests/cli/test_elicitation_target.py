"""Tests for the turn's elicitation target (UN-30320)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from unique_sdk.cli.cli import main
from unique_sdk.cli.identity import (
    TURN_IDENTITY_ENV_VAR,
    ElicitationTarget,
    TurnIdentityError,
    read_turn_identity,
    resolve_elicitation_target,
)

pytestmark = pytest.mark.ai

_TARGET = {
    "chat_id": "chat-parent",
    "message_id": "msg-parent",
    "header": "Sub-agent «Client Researcher» needs your input",
    "metadata": {
        "subAgentName": "Client Researcher",
        "subAgentChatId": "chat-child",
        "subAgentMessageId": "msg-child-user",
    },
}
_ENV = {"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"}


def _write_identity(path: Path, *, target: object = None) -> Path:
    payload: dict[str, object] = {"message_id": "msg-child", "chat_id": "chat-child"}
    if target is not None:
        payload["elicitation_target"] = target
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_read__file_with_target__returns_the_target(tmp_path: Path) -> None:
    path = _write_identity(tmp_path / "turn-identity.json", target=_TARGET)

    identity = read_turn_identity(path)

    assert identity is not None
    assert identity.chat_id == "chat-child"
    assert identity.elicitation_target == ElicitationTarget(
        chat_id="chat-parent",
        message_id="msg-parent",
        header="Sub-agent «Client Researcher» needs your input",
        metadata=_TARGET["metadata"],  # type: ignore[arg-type]
    )


def test_read__file_without_target__has_no_target(tmp_path: Path) -> None:
    path = _write_identity(tmp_path / "turn-identity.json")

    identity = read_turn_identity(path)

    assert identity is not None
    assert identity.elicitation_target is None


@pytest.mark.parametrize(
    "target",
    ["chat-parent", {"chat_id": "chat-parent"}, {"chat_id": " ", "message_id": "m"}],
)
def test_read__malformed_target__fails_loud(tmp_path: Path, target: object) -> None:
    path = _write_identity(tmp_path / "turn-identity.json", target=target)

    with pytest.raises(TurnIdentityError, match="elicitation_target"):
        _ = read_turn_identity(path)


def test_resolve__no_identity_file__returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(TURN_IDENTITY_ENV_VAR, raising=False)

    assert resolve_elicitation_target() is None


def test_with_header__no_header__keeps_the_message() -> None:
    target = ElicitationTarget(chat_id="c", message_id="m")

    assert target.with_header("Which region?") == "Which region?"


@patch("unique_sdk.cli.cli.cmd_elicit_ask", return_value="ok")
def test_elicit_ask__turn_has_target__asks_in_the_target_chat(
    mock_ask: MagicMock, tmp_path: Path
) -> None:
    path = _write_identity(tmp_path / "turn-identity.json", target=_TARGET)

    result = CliRunner().invoke(
        main,
        [
            "elicit",
            "ask",
            "Which region?",
            "--chat-id",
            "chat-child",
            "--metadata",
            "a=b",
        ],
        env={**_ENV, TURN_IDENTITY_ENV_VAR: str(path)},
    )

    assert result.exit_code == 0, result.output
    kwargs = mock_ask.call_args.kwargs
    assert kwargs["chat_id"] == "chat-parent"
    assert kwargs["message_id"] == "msg-parent"
    assert kwargs["message"] == (
        "Sub-agent «Client Researcher» needs your input\n\nWhich region?"
    )
    assert dict(kwargs["metadata"]) == {"a": "b", **_TARGET["metadata"]}  # type: ignore[dict-item]


@patch("unique_sdk.cli.cli.cmd_elicit_create", return_value="ok")
def test_elicit_create__turn_has_target__creates_in_the_target_chat(
    mock_create: MagicMock, tmp_path: Path
) -> None:
    path = _write_identity(tmp_path / "turn-identity.json", target=_TARGET)

    result = CliRunner().invoke(
        main,
        [
            "elicit",
            "create",
            "Open the form",
            "--mode",
            "URL",
            "--tool-name",
            "survey",
            "--url",
            "https://example.com/s/1",
        ],
        env={**_ENV, TURN_IDENTITY_ENV_VAR: str(path)},
    )

    assert result.exit_code == 0, result.output
    kwargs = mock_create.call_args.kwargs
    assert kwargs["chat_id"] == "chat-parent"
    assert kwargs["message_id"] == "msg-parent"
    assert kwargs["message"].startswith("Sub-agent «Client Researcher»")


@patch("unique_sdk.cli.cli.cmd_elicit_ask", return_value="ok")
def test_elicit_ask__turn_has_no_target__asks_in_its_own_chat(
    mock_ask: MagicMock, tmp_path: Path
) -> None:
    path = _write_identity(tmp_path / "turn-identity.json")

    result = CliRunner().invoke(
        main,
        ["elicit", "ask", "Which region?"],
        env={**_ENV, TURN_IDENTITY_ENV_VAR: str(path)},
    )

    assert result.exit_code == 0, result.output
    kwargs = mock_ask.call_args.kwargs
    assert kwargs["chat_id"] == "chat-child"
    assert kwargs["message_id"] == "msg-child"
    assert kwargs["message"] == "Which region?"
    assert kwargs["metadata"] is None
