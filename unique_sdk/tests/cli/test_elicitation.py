"""Tests for the ``elicit`` CLI command group.

Covers :mod:`unique_sdk.cli.commands.elicitation`, the three elicitation
formatters in :mod:`unique_sdk.cli.formatting`, and the ``elicit`` subcommand
dispatch in :mod:`unique_sdk.cli.shell`.
"""

from __future__ import annotations

import json
from io import StringIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import unique_sdk
from unique_sdk.cli.commands.elicitation import (
    _build_create_params,
    _parse_json_arg,
    _parse_metadata_pairs,
    cmd_elicit_ask,
    cmd_elicit_create,
    cmd_elicit_get,
    cmd_elicit_pending,
    cmd_elicit_respond,
    cmd_elicit_wait,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.formatting import (
    format_elicitation,
    format_elicitation_response,
    format_pending_elicitations,
)
from unique_sdk.cli.shell import UniqueShell
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


def _shell() -> UniqueShell:
    return UniqueShell(_state())


def _capture(shell: UniqueShell, command: str) -> str:
    buf = StringIO()
    shell._print = lambda text: buf.write(text + "\n")  # type: ignore[assignment]
    shell.onecmd(command)
    return buf.getvalue()


def _elicitation(
    *,
    eid: str = "elicit_abc",
    status: str = "PENDING",
    mode: str = "FORM",
    response_content: Any = None,
    schema: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tool_name: str | None = "agent_question",
    message: str = "What should I do?",
) -> dict[str, Any]:
    return {
        "id": eid,
        "status": status,
        "mode": mode,
        "source": "AGENT",
        "toolName": tool_name,
        "message": message,
        "schema": schema,
        "url": None,
        "chatId": "chat_1",
        "messageId": None,
        "externalElicitationId": None,
        "metadata": metadata,
        "responseContent": response_content,
        "respondedAt": "2026-04-16T09:00:00Z" if response_content else None,
        "expiresAt": "2026-04-16T10:00:00Z",
        "createdAt": "2026-04-16T08:00:00Z",
        "updatedAt": "2026-04-16T08:30:00Z",
    }


# --- Helper parsers -----------------------------------------------------


class TestParseJsonArg:
    def test_none_returns_none(self) -> None:
        assert _parse_json_arg(None, field="--schema") is None

    def test_valid_object(self) -> None:
        assert _parse_json_arg('{"a": 1}', field="--schema") == {"a": 1}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON for --schema"):
            _parse_json_arg("not-json", field="--schema")

    def test_non_object_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a JSON object"):
            _parse_json_arg("[1, 2]", field="--schema")


class TestParseMetadataPairs:
    def test_none(self) -> None:
        assert _parse_metadata_pairs(None) is None

    def test_empty(self) -> None:
        assert _parse_metadata_pairs([]) is None

    def test_pairs(self) -> None:
        result = _parse_metadata_pairs([("k1", "v1"), ("k2", "v2")])
        assert result == {"k1": "v1", "k2": "v2"}


class TestBuildCreateParams:
    def test_minimal(self) -> None:
        params = _build_create_params(
            mode="FORM",
            message="Hi",
            tool_name="tool",
            schema=None,
            url=None,
            chat_id=None,
            message_id=None,
            expires_in_seconds=None,
            external_elicitation_id=None,
            metadata=None,
        )
        assert params == {"mode": "FORM", "message": "Hi", "toolName": "tool"}

    def test_all_fields(self) -> None:
        params = _build_create_params(
            mode="URL",
            message="Click",
            tool_name="tool",
            schema={"type": "object"},
            url="https://x",
            chat_id="c1",
            message_id="m1",
            expires_in_seconds=60,
            external_elicitation_id="ext_1",
            metadata={"foo": "bar"},
        )
        assert params["mode"] == "URL"
        assert params["url"] == "https://x"
        assert params["chatId"] == "c1"
        assert params["messageId"] == "m1"
        assert params["expiresInSeconds"] == 60
        assert params["externalElicitationId"] == "ext_1"
        assert params["metadata"] == {"foo": "bar"}
        assert params["schema"] == {"type": "object"}


# --- Commands -----------------------------------------------------------


class TestElicitCreate:
    @patch("unique_sdk.Elicitation.create_elicitation")
    def test_form_success(self, mock: MagicMock) -> None:
        mock.return_value = _elicitation()
        result = cmd_elicit_create(
            _state(),
            mode="form",
            message="Confirm?",
            tool_name="confirm",
            schema='{"type": "object"}',
        )
        assert "Created elicitation elicit_abc" in result
        call_kwargs = mock.call_args[1]
        assert call_kwargs["mode"] == "FORM"
        assert call_kwargs["schema"] == {"type": "object"}

    @patch("unique_sdk.Elicitation.create_elicitation")
    def test_url_success(self, mock: MagicMock) -> None:
        mock.return_value = _elicitation(mode="URL")
        result = cmd_elicit_create(
            _state(),
            mode="URL",
            message="Open",
            tool_name="open",
            url="https://example.com",
            metadata=[("k", "v")],
        )
        assert "Created elicitation" in result
        assert mock.call_args[1]["metadata"] == {"k": "v"}

    def test_invalid_mode(self) -> None:
        result = cmd_elicit_create(_state(), mode="BOGUS", message="x", tool_name="t")
        assert "invalid mode" in result

    def test_form_requires_schema(self) -> None:
        result = cmd_elicit_create(_state(), mode="FORM", message="x", tool_name="t")
        assert "--schema is required" in result

    def test_url_requires_url(self) -> None:
        result = cmd_elicit_create(_state(), mode="URL", message="x", tool_name="t")
        assert "--url is required" in result

    def test_invalid_schema_json(self) -> None:
        result = cmd_elicit_create(
            _state(),
            mode="FORM",
            message="x",
            tool_name="t",
            schema="not-json",
        )
        assert "Invalid JSON" in result

    @patch("unique_sdk.Elicitation.create_elicitation")
    def test_api_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("boom")
        result = cmd_elicit_create(
            _state(),
            mode="FORM",
            message="x",
            tool_name="t",
            schema='{"type":"object"}',
        )
        assert "elicit:" in result


class TestElicitPending:
    @patch("unique_sdk.Elicitation.get_pending_elicitations")
    def test_empty(self, mock: MagicMock) -> None:
        mock.return_value = {"elicitations": []}
        assert "No pending" in cmd_elicit_pending(_state())

    @patch("unique_sdk.Elicitation.get_pending_elicitations")
    def test_with_items(self, mock: MagicMock) -> None:
        mock.return_value = {"elicitations": [_elicitation()]}
        out = cmd_elicit_pending(_state())
        assert "1 pending elicitation" in out
        assert "elicit_abc" in out

    @patch("unique_sdk.Elicitation.get_pending_elicitations")
    def test_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("fail")
        assert "elicit:" in cmd_elicit_pending(_state())


class TestElicitGet:
    @patch("unique_sdk.Elicitation.get_elicitation")
    def test_ok(self, mock: MagicMock) -> None:
        mock.return_value = _elicitation()
        out = cmd_elicit_get(_state(), "elicit_abc")
        assert "elicit_abc" in out

    @patch("unique_sdk.Elicitation.get_elicitation")
    def test_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("nope")
        assert "elicit:" in cmd_elicit_get(_state(), "x")


class TestElicitRespond:
    @patch("unique_sdk.Elicitation.respond_to_elicitation")
    def test_accept(self, mock: MagicMock) -> None:
        mock.return_value = {"success": True}
        result = cmd_elicit_respond(
            _state(),
            "elicit_abc",
            action="ACCEPT",
            content='{"answer": "yes"}',
        )
        assert "OK" in result
        assert mock.call_args[1]["content"] == {"answer": "yes"}

    @patch("unique_sdk.Elicitation.respond_to_elicitation")
    def test_decline(self, mock: MagicMock) -> None:
        mock.return_value = {"success": True}
        result = cmd_elicit_respond(_state(), "elicit_abc", action="decline")
        assert "OK" in result
        assert mock.call_args[1]["action"] == "DECLINE"
        assert "content" not in mock.call_args[1]

    def test_invalid_action(self) -> None:
        result = cmd_elicit_respond(_state(), "x", action="FROB")
        assert "invalid action" in result

    def test_accept_requires_content(self) -> None:
        result = cmd_elicit_respond(_state(), "x", action="ACCEPT")
        assert "--content" in result

    def test_invalid_content_json(self) -> None:
        result = cmd_elicit_respond(_state(), "x", action="ACCEPT", content="not-json")
        assert "Invalid JSON" in result

    @patch("unique_sdk.Elicitation.respond_to_elicitation")
    def test_api_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("fail")
        result = cmd_elicit_respond(_state(), "x", action="CANCEL")
        assert "elicit:" in result


class TestElicitWait:
    @patch("unique_sdk.Elicitation.get_elicitation")
    def test_immediately_terminal(self, mock: MagicMock) -> None:
        mock.return_value = _elicitation(
            status="RESPONDED", response_content={"answer": "yes"}
        )
        result = cmd_elicit_wait(_state(), "elicit_abc", timeout=5)
        assert "RESPONDED" in result
        assert '"answer"' in result

    @patch("unique_sdk.cli.commands.elicitation.time.sleep")
    @patch("unique_sdk.Elicitation.get_elicitation")
    def test_polls_until_terminal(
        self, mock_get: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_get.side_effect = [
            _elicitation(status="PENDING"),
            _elicitation(status="PENDING"),
            _elicitation(status="DECLINED"),
        ]
        result = cmd_elicit_wait(_state(), "elicit_abc", timeout=30, poll_interval=0.01)
        assert "DECLINED" in result
        assert mock_sleep.call_count == 2

    @patch("unique_sdk.cli.commands.elicitation.time.sleep")
    @patch("unique_sdk.cli.commands.elicitation.time.monotonic")
    @patch("unique_sdk.Elicitation.get_elicitation")
    def test_timeout(
        self,
        mock_get: MagicMock,
        mock_monotonic: MagicMock,
        mock_sleep: MagicMock,
    ) -> None:
        mock_get.return_value = _elicitation(status="PENDING")
        mock_monotonic.side_effect = [0.0, 100.0, 200.0]
        result = cmd_elicit_wait(_state(), "elicit_abc", timeout=10)
        assert "timed out after 10s" in result

    @patch("unique_sdk.Elicitation.get_elicitation")
    def test_api_error(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("fail")
        assert "elicit:" in cmd_elicit_wait(_state(), "x", timeout=1)


class TestElicitAsk:
    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.Elicitation.create_elicitation")
    def test_default_schema(self, mock_create: MagicMock, mock_get: MagicMock) -> None:
        mock_create.return_value = _elicitation()
        mock_get.return_value = _elicitation(
            status="RESPONDED", response_content={"answer": "hello"}
        )
        result = cmd_elicit_ask(_state(), message="What?")
        assert "RESPONDED" in result
        sent_schema = mock_create.call_args[1]["schema"]
        assert sent_schema["required"] == ["answer"]

    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.Elicitation.create_elicitation")
    def test_custom_schema_and_metadata(
        self, mock_create: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_create.return_value = _elicitation()
        mock_get.return_value = _elicitation(
            status="RESPONDED", response_content={"choice": "A"}
        )
        result = cmd_elicit_ask(
            _state(),
            message="Pick",
            schema='{"type": "object", "properties": {"choice": {"type": "string"}}}',
            metadata=[("src", "cli")],
        )
        assert "RESPONDED" in result
        assert mock_create.call_args[1]["metadata"] == {"src": "cli"}

    def test_invalid_schema_json(self) -> None:
        result = cmd_elicit_ask(_state(), message="x", schema="not-json")
        assert "Invalid JSON" in result

    @patch("unique_sdk.Elicitation.create_elicitation")
    def test_missing_id_from_platform(self, mock_create: MagicMock) -> None:
        mock_create.return_value = {}
        result = cmd_elicit_ask(_state(), message="x")
        assert "did not return an elicitation id" in result

    @patch("unique_sdk.Elicitation.create_elicitation")
    def test_api_error(self, mock_create: MagicMock) -> None:
        mock_create.side_effect = unique_sdk.APIError("fail")
        result = cmd_elicit_ask(_state(), message="x")
        assert "elicit:" in result


# --- Formatters ---------------------------------------------------------


class TestFormatElicitation:
    def test_pending_minimal(self) -> None:
        out = format_elicitation(_elicitation())
        assert "elicit_abc" in out
        assert "PENDING" in out
        assert "FORM" in out
        assert "Response:" in out
        assert "(none)" in out

    def test_with_response_schema_metadata(self) -> None:
        out = format_elicitation(
            _elicitation(
                status="RESPONDED",
                response_content={"answer": "yes"},
                schema={"type": "object"},
                metadata={"k": "v"},
            )
        )
        assert '"answer"' in out
        assert '"type"' in out
        assert '"k"' in out

    def test_empty_fields(self) -> None:
        out = format_elicitation(
            {
                "id": "e1",
                "status": "PENDING",
                "mode": "FORM",
                "toolName": None,
                "url": None,
                "chatId": None,
                "messageId": None,
                "externalElicitationId": None,
            }
        )
        assert "e1" in out
        assert "PENDING" in out


class TestFormatPendingElicitations:
    def test_empty(self) -> None:
        assert format_pending_elicitations([]) == "No pending elicitations."

    def test_truncates_long_message(self) -> None:
        long_msg = "x" * 200
        out = format_pending_elicitations([_elicitation(message=long_msg)])
        assert "..." in out

    def test_multiple(self) -> None:
        out = format_pending_elicitations(
            [_elicitation(eid="e1"), _elicitation(eid="e2")]
        )
        assert "2 pending elicitation" in out
        assert "e1" in out and "e2" in out


class TestFormatElicitationResponse:
    def test_success(self) -> None:
        out = format_elicitation_response({"success": True}, "elicit_abc", "ACCEPT")
        assert "OK" in out
        assert "ACCEPT" in out
        assert "elicit_abc" in out

    def test_failure_with_detail(self) -> None:
        out = format_elicitation_response(
            {"success": False, "message": "nope"}, "elicit_abc", "DECLINE"
        )
        assert "FAILED" in out
        assert "nope" in out


# --- Shell dispatch -----------------------------------------------------


class TestShellElicit:
    def test_help_no_args(self) -> None:
        out = _capture(_shell(), "elicit")
        assert "Usage: elicit" in out

    def test_unknown_subcommand(self) -> None:
        out = _capture(_shell(), "elicit bogus")
        assert "Unknown subcommand" in out

    @patch("unique_sdk.cli.shell.cmd_elicit_pending")
    def test_pending(self, mock: MagicMock) -> None:
        mock.return_value = "PENDING_OUT"
        out = _capture(_shell(), "elicit pending")
        assert "PENDING_OUT" in out

    def test_get_requires_id(self) -> None:
        out = _capture(_shell(), "elicit get")
        assert "Usage: elicit get" in out

    @patch("unique_sdk.cli.shell.cmd_elicit_get")
    def test_get_forwards(self, mock: MagicMock) -> None:
        mock.return_value = "GOT"
        out = _capture(_shell(), "elicit get elicit_abc")
        assert "GOT" in out
        assert mock.call_args[0][1] == "elicit_abc"

    def test_ask_without_message(self) -> None:
        out = _capture(_shell(), "elicit ask")
        assert "Usage: elicit ask" in out

    @patch("unique_sdk.cli.shell.cmd_elicit_ask")
    def test_ask_forwards(self, mock: MagicMock) -> None:
        mock.return_value = "ASKED"
        out = _capture(
            _shell(),
            'elicit ask "What?" --timeout 30 --poll-interval 1.5 '
            "--metadata src=cli --chat-id c1",
        )
        assert "ASKED" in out
        kw = mock.call_args[1]
        assert kw["message"] == "What?"
        assert kw["timeout"] == 30
        assert kw["poll_interval"] == 1.5
        assert kw["chat_id"] == "c1"
        assert kw["metadata"] == [("src", "cli")]

    def test_ask_invalid_timeout(self) -> None:
        out = _capture(_shell(), 'elicit ask "x" --timeout abc')
        assert "Invalid --timeout" in out

    def test_ask_invalid_poll_interval(self) -> None:
        out = _capture(_shell(), 'elicit ask "x" --poll-interval abc')
        assert "Invalid --poll-interval" in out

    def test_ask_invalid_expires_in(self) -> None:
        out = _capture(_shell(), 'elicit ask "x" --expires-in abc')
        assert "Invalid --expires-in" in out

    def test_ask_invalid_metadata(self) -> None:
        out = _capture(_shell(), 'elicit ask "x" --metadata badformat')
        assert "Invalid metadata format" in out

    def test_create_without_message(self) -> None:
        out = _capture(_shell(), "elicit create")
        assert "Usage: elicit create" in out

    def test_create_requires_mode(self) -> None:
        out = _capture(_shell(), 'elicit create "msg" --tool-name t')
        assert "--mode is required" in out

    def test_create_requires_tool_name(self) -> None:
        out = _capture(_shell(), 'elicit create "msg" --mode FORM')
        assert "--tool-name" in out

    @patch("unique_sdk.cli.shell.cmd_elicit_create")
    def test_create_forwards(self, mock: MagicMock) -> None:
        mock.return_value = "CREATED"
        schema = json.dumps({"type": "object"})
        out = _capture(
            _shell(),
            f'elicit create "Do it?" --mode FORM --tool-name confirm '
            f"--schema '{schema}' --external-id ext_1 --message-id m1 "
            f"--expires-in 60",
        )
        assert "CREATED" in out
        kw = mock.call_args[1]
        assert kw["mode"] == "FORM"
        assert kw["tool_name"] == "confirm"
        assert kw["external_elicitation_id"] == "ext_1"
        assert kw["message_id"] == "m1"
        assert kw["expires_in_seconds"] == 60

    def test_wait_requires_id(self) -> None:
        out = _capture(_shell(), "elicit wait")
        assert "Usage: elicit wait" in out

    @patch("unique_sdk.cli.shell.cmd_elicit_wait")
    def test_wait_forwards(self, mock: MagicMock) -> None:
        mock.return_value = "WAITED"
        out = _capture(_shell(), "elicit wait elicit_abc --timeout 5")
        assert "WAITED" in out
        assert mock.call_args[0][1] == "elicit_abc"
        assert mock.call_args[1]["timeout"] == 5

    def test_respond_requires_id(self) -> None:
        out = _capture(_shell(), "elicit respond")
        assert "Usage: elicit respond" in out

    def test_respond_requires_action(self) -> None:
        out = _capture(_shell(), "elicit respond elicit_abc")
        assert "--action" in out

    @patch("unique_sdk.cli.shell.cmd_elicit_respond")
    def test_respond_forwards(self, mock: MagicMock) -> None:
        mock.return_value = "RESPONDED"
        out = _capture(
            _shell(),
            "elicit respond elicit_abc --action ACCEPT --content '{\"a\":1}'",
        )
        assert "RESPONDED" in out
        kw = mock.call_args[1]
        assert kw["action"] == "ACCEPT"
        assert kw["content"] == '{"a":1}'
