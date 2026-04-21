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
    META_CLEANUP_MODE,
    META_PLACEHOLDER_CHAT_ID,
    META_PLACEHOLDER_MESSAGE_ID,
    META_PLACEHOLDER_STEP_ID,
    _build_create_params,
    _extract_visibility_context,
    _parse_json_arg,
    _parse_metadata_pairs,
    _resolve_assistant_id,
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
    def test_accepts_plain_list_response(self, mock: MagicMock) -> None:
        """Regression: backend returns a raw array, not wrapped in dict."""
        mock.return_value = [_elicitation(eid="e1"), _elicitation(eid="e2")]
        out = cmd_elicit_pending(_state())
        assert "2 pending elicitation" in out
        assert "e1" in out and "e2" in out

    @patch("unique_sdk.Elicitation.get_pending_elicitations")
    def test_accepts_empty_list_response(self, mock: MagicMock) -> None:
        mock.return_value = []
        assert "No pending" in cmd_elicit_pending(_state())

    @patch("unique_sdk.Elicitation.get_pending_elicitations")
    def test_accepts_wrapped_object_response(self, mock: MagicMock) -> None:
        mock.return_value = {"elicitations": [_elicitation()]}
        out = cmd_elicit_pending(_state())
        assert "1 pending elicitation" in out

    @patch("unique_sdk.Elicitation.get_pending_elicitations")
    def test_handles_unexpected_response_type(self, mock: MagicMock) -> None:
        mock.return_value = None
        assert "No pending" in cmd_elicit_pending(_state())

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
    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.Elicitation.respond_to_elicitation")
    def test_accept(self, mock: MagicMock, mock_get: MagicMock) -> None:
        mock.return_value = {"success": True}
        mock_get.return_value = _elicitation()
        result = cmd_elicit_respond(
            _state(),
            "elicit_abc",
            action="ACCEPT",
            content='{"answer": "yes"}',
        )
        assert "OK" in result
        assert mock.call_args[1]["content"] == {"answer": "yes"}

    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.Elicitation.respond_to_elicitation")
    def test_decline(self, mock: MagicMock, mock_get: MagicMock) -> None:
        mock.return_value = {"success": True}
        mock_get.return_value = _elicitation()
        result = cmd_elicit_respond(_state(), "elicit_abc", action="decline")
        assert "OK" in result
        assert mock.call_args[1]["action"] == "DECLINE"
        assert "content" not in mock.call_args[1]

    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.Elicitation.respond_to_elicitation")
    def test_reject(self, mock: MagicMock, mock_get: MagicMock) -> None:
        """Regression: ``REJECT`` is a valid action accepted by the backend."""
        mock.return_value = {"success": True}
        mock_get.return_value = _elicitation()
        result = cmd_elicit_respond(_state(), "elicit_abc", action="reject")
        assert "OK" in result
        assert mock.call_args[1]["action"] == "REJECT"
        assert "content" not in mock.call_args[1]

    def test_invalid_action(self) -> None:
        result = cmd_elicit_respond(_state(), "x", action="FROB")
        assert "invalid action" in result
        assert "REJECT" in result

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
    def test_terminates_on_accepted_status(
        self, mock_get: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Regression: platform persists ``ACCEPTED`` when a user confirms a FORM."""
        mock_get.return_value = _elicitation(
            status="ACCEPTED", response_content={"answer": "yes"}
        )
        result = cmd_elicit_wait(_state(), "elicit_abc", timeout=30)
        assert "ACCEPTED" in result
        assert "timed out" not in result
        assert mock_sleep.call_count == 0

    @patch("unique_sdk.cli.commands.elicitation.time.sleep")
    @patch("unique_sdk.Elicitation.get_elicitation")
    def test_terminates_on_rejected_status(
        self, mock_get: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Regression: platform persists ``REJECTED`` when a user rejects a FORM."""
        mock_get.return_value = _elicitation(status="REJECTED")
        result = cmd_elicit_wait(_state(), "elicit_abc", timeout=30)
        assert "REJECTED" in result
        assert "timed out" not in result
        assert mock_sleep.call_count == 0

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


# --- Visibility workaround (UN-19815) -----------------------------------


def _placeholder_message(
    eid: str = "msg_placeholder", assistant_id: str = "assistant_1"
) -> dict[str, Any]:
    return {
        "id": eid,
        "role": "ASSISTANT",
        "assistantId": assistant_id,
        "text": None,
        "completedAt": None,
        "chatId": "chat_1",
    }


def _step(sid: str = "step_placeholder") -> dict[str, Any]:
    return {"id": sid, "status": "RUNNING", "text": "Waiting…", "order": 0}


def _visible_elicitation(
    *,
    eid: str = "elicit_abc",
    status: str = "PENDING",
    response_content: Any = None,
    chat_id: str = "chat_1",
    placeholder_message_id: str = "msg_placeholder",
    placeholder_step_id: str = "step_placeholder",
    cleanup_mode: str = "collapse",
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "messageLogId": placeholder_step_id,
        META_PLACEHOLDER_MESSAGE_ID: placeholder_message_id,
        META_PLACEHOLDER_STEP_ID: placeholder_step_id,
        META_PLACEHOLDER_CHAT_ID: chat_id,
        META_CLEANUP_MODE: cleanup_mode,
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return _elicitation(
        eid=eid,
        status=status,
        response_content=response_content,
        metadata=metadata,
    )


class TestResolveAssistantId:
    def test_env_var_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNIQUE_ASSISTANT_ID", "from_env")
        # no Message.list call should be needed
        assert _resolve_assistant_id(_state(), "chat_1") == "from_env"

    @patch("unique_sdk.Message.list")
    def test_picks_latest_assistant_message(
        self,
        mock_list: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("UNIQUE_ASSISTANT_ID", raising=False)
        mock_list.return_value = [
            {"role": "USER", "assistantId": "should_ignore"},
            {"role": "ASSISTANT", "assistantId": "older"},
            {"role": "ASSISTANT", "assistantId": "newest"},
        ]
        assert _resolve_assistant_id(_state(), "chat_1") == "newest"

    @patch("unique_sdk.Message.list")
    def test_none_when_no_assistant(
        self,
        mock_list: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("UNIQUE_ASSISTANT_ID", raising=False)
        mock_list.return_value = [{"role": "USER", "assistantId": "x"}]
        assert _resolve_assistant_id(_state(), "chat_1") is None

    @patch("unique_sdk.Message.list")
    def test_none_when_list_raises(
        self,
        mock_list: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("UNIQUE_ASSISTANT_ID", raising=False)
        mock_list.side_effect = unique_sdk.APIError("boom")
        assert _resolve_assistant_id(_state(), "chat_1") is None

    @patch("unique_sdk.Message.list")
    def test_falls_back_to_debug_info_assistant_id(
        self,
        mock_list: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Public REST omits ``assistantId`` at the top level and nests it
        under ``debugInfo.assistant.id``; the resolver must look there too,
        otherwise the visibility workaround cannot auto-resolve the
        assistant for chats fetched via the gateway.
        """
        monkeypatch.delenv("UNIQUE_ASSISTANT_ID", raising=False)
        mock_list.return_value = [
            {"role": "USER"},
            {
                "role": "ASSISTANT",
                "debugInfo": {
                    "assistant": {"id": "assistant_from_debug_info", "name": "X"},
                },
            },
        ]
        assert _resolve_assistant_id(_state(), "chat_1") == "assistant_from_debug_info"

    @patch("unique_sdk.Message.list")
    def test_falls_back_to_debug_info_on_user_message(
        self,
        mock_list: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Observed on the QA public gateway: ASSISTANT messages have
        ``debugInfo.assistant == None`` while USER messages carry the
        populated ``debugInfo.assistant.id``. Since the chat is bound to a
        single assistant regardless of message role, the resolver must be
        willing to read that field from any message.
        """
        monkeypatch.delenv("UNIQUE_ASSISTANT_ID", raising=False)
        mock_list.return_value = [
            {
                "role": "USER",
                "debugInfo": {"assistant": {"id": "assistant_from_user_msg"}},
            },
            {"role": "ASSISTANT", "debugInfo": {"assistant": None}},
        ]
        assert _resolve_assistant_id(_state(), "chat_1") == "assistant_from_user_msg"


class TestExtractVisibilityContext:
    def test_no_metadata(self) -> None:
        assert _extract_visibility_context({"status": "PENDING"}) is None

    def test_missing_markers(self) -> None:
        assert _extract_visibility_context({"metadata": {"messageLogId": "x"}}) is None

    def test_with_markers_defaults_collapse(self) -> None:
        ctx = _extract_visibility_context(_visible_elicitation())
        assert ctx == ("chat_1", "msg_placeholder", "step_placeholder", "collapse")

    def test_with_markers_delete_mode(self) -> None:
        ctx = _extract_visibility_context(_visible_elicitation(cleanup_mode="delete"))
        assert ctx is not None
        assert ctx[3] == "delete"

    def test_unknown_cleanup_mode_defaults_to_collapse(self) -> None:
        ctx = _extract_visibility_context(_visible_elicitation(cleanup_mode="garbage"))
        assert ctx is not None
        assert ctx[3] == "collapse"


@patch("unique_sdk.Message.delete")
@patch("unique_sdk.Message.modify")
@patch("unique_sdk.Message.create")
@patch("unique_sdk.MessageLog.update")
@patch("unique_sdk.MessageLog.create")
@patch("unique_sdk.Elicitation.get_elicitation")
@patch("unique_sdk.Elicitation.create_elicitation")
class TestVisibleAsk:
    """``cmd_elicit_ask`` with the UN-19815 visibility workaround."""

    def test_visible_default_creates_placeholder_and_collapses(
        self,
        mock_create_elicit: MagicMock,
        mock_get_elicit: MagicMock,
        mock_log_create: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_create: MagicMock,
        mock_msg_modify: MagicMock,
        mock_msg_delete: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("UNIQUE_ASSISTANT_ID", "assistant_1")
        mock_msg_create.return_value = _placeholder_message()
        mock_log_create.return_value = _step()
        mock_create_elicit.return_value = _visible_elicitation()
        mock_get_elicit.return_value = _visible_elicitation(
            status="ACCEPTED", response_content={"answer": "yes"}
        )

        result = cmd_elicit_ask(_state(), message="What?", chat_id="chat_1", timeout=5)

        assert "ACCEPTED" in result
        # Placeholder created with empty text and no completedAt
        placeholder_kwargs = mock_msg_create.call_args[1]
        assert placeholder_kwargs["role"] == "ASSISTANT"
        assert placeholder_kwargs["text"] is None
        assert placeholder_kwargs["completedAt"] is None
        assert placeholder_kwargs["assistantId"] == "assistant_1"
        # Step created in RUNNING state
        step_kwargs = mock_log_create.call_args[1]
        assert step_kwargs["messageId"] == "msg_placeholder"
        assert step_kwargs["status"] == "RUNNING"
        # Elicitation carries messageId + metadata.messageLogId + markers
        elicit_kwargs = mock_create_elicit.call_args[1]
        assert elicit_kwargs["messageId"] == "msg_placeholder"
        meta = elicit_kwargs["metadata"]
        assert meta["messageLogId"] == "step_placeholder"
        assert meta[META_PLACEHOLDER_MESSAGE_ID] == "msg_placeholder"
        assert meta[META_PLACEHOLDER_STEP_ID] == "step_placeholder"
        assert meta[META_PLACEHOLDER_CHAT_ID] == "chat_1"
        assert meta[META_CLEANUP_MODE] == "collapse"
        # Cleanup: step completed, message modified (collapse), not deleted
        assert mock_log_update.call_count == 1
        log_update_kwargs = mock_log_update.call_args[1]
        assert log_update_kwargs["status"] == "COMPLETED"
        assert mock_msg_modify.call_count == 1
        msg_modify_kwargs = mock_msg_modify.call_args[1]
        assert msg_modify_kwargs["id"] == "msg_placeholder"
        assert msg_modify_kwargs["chatId"] == "chat_1"
        assert msg_modify_kwargs["completedAt"] is not None
        assert mock_msg_delete.call_count == 0

    def test_no_visible_skips_workaround(
        self,
        mock_create_elicit: MagicMock,
        mock_get_elicit: MagicMock,
        mock_log_create: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_create: MagicMock,
        mock_msg_modify: MagicMock,
        mock_msg_delete: MagicMock,
    ) -> None:
        mock_create_elicit.return_value = _elicitation()
        mock_get_elicit.return_value = _elicitation(
            status="RESPONDED", response_content={"answer": "yes"}
        )

        result = cmd_elicit_ask(
            _state(),
            message="What?",
            chat_id="chat_1",
            timeout=5,
            visible=False,
        )

        assert "RESPONDED" in result
        assert mock_msg_create.call_count == 0
        assert mock_log_create.call_count == 0
        assert mock_msg_modify.call_count == 0
        assert mock_msg_delete.call_count == 0
        # Elicitation should not carry visibility markers
        elicit_kwargs = mock_create_elicit.call_args[1]
        assert "messageId" not in elicit_kwargs
        assert elicit_kwargs.get("metadata") is None

    def test_without_chat_id_skips_workaround(
        self,
        mock_create_elicit: MagicMock,
        mock_get_elicit: MagicMock,
        mock_log_create: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_create: MagicMock,
        mock_msg_modify: MagicMock,
        mock_msg_delete: MagicMock,
    ) -> None:
        mock_create_elicit.return_value = _elicitation()
        mock_get_elicit.return_value = _elicitation(
            status="RESPONDED", response_content={"answer": "yes"}
        )

        result = cmd_elicit_ask(_state(), message="What?", timeout=5)

        assert "RESPONDED" in result
        assert mock_msg_create.call_count == 0

    def test_explicit_message_id_skips_workaround(
        self,
        mock_create_elicit: MagicMock,
        mock_get_elicit: MagicMock,
        mock_log_create: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_create: MagicMock,
        mock_msg_modify: MagicMock,
        mock_msg_delete: MagicMock,
    ) -> None:
        """When caller already supplies --message-id we trust them."""
        mock_create_elicit.return_value = _elicitation()
        mock_get_elicit.return_value = _elicitation(
            status="RESPONDED", response_content={"answer": "yes"}
        )

        cmd_elicit_ask(
            _state(),
            message="What?",
            chat_id="chat_1",
            message_id="existing_msg",
            timeout=5,
        )

        assert mock_msg_create.call_count == 0
        elicit_kwargs = mock_create_elicit.call_args[1]
        assert elicit_kwargs["messageId"] == "existing_msg"

    def test_no_assistant_id_returns_error(
        self,
        mock_create_elicit: MagicMock,
        mock_get_elicit: MagicMock,
        mock_log_create: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_create: MagicMock,
        mock_msg_modify: MagicMock,
        mock_msg_delete: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("UNIQUE_ASSISTANT_ID", raising=False)
        with patch("unique_sdk.Message.list", return_value=[]):
            result = cmd_elicit_ask(
                _state(), message="What?", chat_id="chat_1", timeout=5
            )
        assert "cannot ask a visible question without an assistant id" in result
        assert mock_msg_create.call_count == 0
        assert mock_create_elicit.call_count == 0

    def test_cleanup_mode_delete(
        self,
        mock_create_elicit: MagicMock,
        mock_get_elicit: MagicMock,
        mock_log_create: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_create: MagicMock,
        mock_msg_modify: MagicMock,
        mock_msg_delete: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("UNIQUE_ASSISTANT_ID", "assistant_1")
        mock_msg_create.return_value = _placeholder_message()
        mock_log_create.return_value = _step()
        mock_create_elicit.return_value = _visible_elicitation(cleanup_mode="delete")
        mock_get_elicit.return_value = _visible_elicitation(
            status="ACCEPTED", cleanup_mode="delete"
        )

        cmd_elicit_ask(
            _state(),
            message="Delete me",
            chat_id="chat_1",
            cleanup_mode="delete",
            timeout=5,
        )

        assert mock_msg_delete.call_count == 1
        assert mock_msg_delete.call_args[1]["chatId"] == "chat_1"
        assert mock_msg_modify.call_count == 0

    def test_cleanup_on_elicitation_create_failure(
        self,
        mock_create_elicit: MagicMock,
        mock_get_elicit: MagicMock,
        mock_log_create: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_create: MagicMock,
        mock_msg_modify: MagicMock,
        mock_msg_delete: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("UNIQUE_ASSISTANT_ID", "assistant_1")
        mock_msg_create.return_value = _placeholder_message()
        mock_log_create.return_value = _step()
        mock_create_elicit.side_effect = unique_sdk.APIError("boom")

        result = cmd_elicit_ask(_state(), message="What?", chat_id="chat_1", timeout=5)

        assert "elicit:" in result
        # Placeholder was torn down even though elicit creation failed
        assert mock_log_update.call_count == 1
        assert mock_msg_modify.call_count == 1

    def test_cleanup_on_wait_timeout(
        self,
        mock_create_elicit: MagicMock,
        mock_get_elicit: MagicMock,
        mock_log_create: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_create: MagicMock,
        mock_msg_modify: MagicMock,
        mock_msg_delete: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("UNIQUE_ASSISTANT_ID", "assistant_1")
        mock_msg_create.return_value = _placeholder_message()
        mock_log_create.return_value = _step()
        mock_create_elicit.return_value = _visible_elicitation()
        mock_get_elicit.return_value = _visible_elicitation(status="PENDING")

        with (
            patch(
                "unique_sdk.cli.commands.elicitation.time.monotonic",
                side_effect=[0.0, 100.0, 200.0],
            ),
            patch("unique_sdk.cli.commands.elicitation.time.sleep"),
        ):
            result = cmd_elicit_ask(
                _state(), message="What?", chat_id="chat_1", timeout=10
            )

        assert "timed out" in result
        assert mock_msg_modify.call_count == 1


class TestVisibleCreate:
    @patch("unique_sdk.MessageLog.create")
    @patch("unique_sdk.Message.create")
    @patch("unique_sdk.Elicitation.create_elicitation")
    def test_embeds_markers_and_prints_note(
        self,
        mock_elicit_create: MagicMock,
        mock_msg_create: MagicMock,
        mock_log_create: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("UNIQUE_ASSISTANT_ID", "assistant_1")
        mock_msg_create.return_value = _placeholder_message()
        mock_log_create.return_value = _step()
        mock_elicit_create.return_value = _visible_elicitation()

        result = cmd_elicit_create(
            _state(),
            mode="FORM",
            message="Pick",
            tool_name="pick",
            schema='{"type":"object"}',
            chat_id="chat_1",
        )

        assert "Created elicitation elicit_abc" in result
        assert "placeholder assistant message was created" in result
        kwargs = mock_elicit_create.call_args[1]
        assert kwargs["messageId"] == "msg_placeholder"
        assert kwargs["metadata"][META_PLACEHOLDER_MESSAGE_ID] == "msg_placeholder"


class TestVisibleWaitCleanup:
    @patch("unique_sdk.Message.modify")
    @patch("unique_sdk.MessageLog.update")
    @patch("unique_sdk.Elicitation.get_elicitation")
    def test_wait_cleans_up_on_terminal(
        self,
        mock_get: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_modify: MagicMock,
    ) -> None:
        mock_get.return_value = _visible_elicitation(
            status="REJECTED",
        )
        result = cmd_elicit_wait(_state(), "elicit_abc", timeout=5)
        assert "REJECTED" in result
        assert mock_log_update.call_count == 1
        assert mock_msg_modify.call_count == 1
        # Uses the "other" (non-accepted) collapse text
        assert mock_msg_modify.call_args[1]["text"] == "Clarifying question closed."

    @patch("unique_sdk.Message.modify")
    @patch("unique_sdk.MessageLog.update")
    @patch("unique_sdk.Elicitation.get_elicitation")
    def test_wait_cleanup_silent_on_failure(
        self,
        mock_get: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_modify: MagicMock,
    ) -> None:
        """Cleanup errors must not mask the successful response."""
        mock_get.return_value = _visible_elicitation(status="ACCEPTED")
        mock_log_update.side_effect = unique_sdk.APIError("log boom")
        mock_msg_modify.side_effect = unique_sdk.APIError("modify boom")

        result = cmd_elicit_wait(_state(), "elicit_abc", timeout=5)
        assert "ACCEPTED" in result


class TestVisibleRespondCleanup:
    @patch("unique_sdk.Message.modify")
    @patch("unique_sdk.MessageLog.update")
    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.Elicitation.respond_to_elicitation")
    def test_respond_tears_down_placeholder(
        self,
        mock_respond: MagicMock,
        mock_get: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_modify: MagicMock,
    ) -> None:
        mock_respond.return_value = {"success": True}
        mock_get.return_value = _visible_elicitation(status="ACCEPTED")

        result = cmd_elicit_respond(
            _state(),
            "elicit_abc",
            action="ACCEPT",
            content='{"answer": "yes"}',
        )

        assert "OK" in result
        assert mock_log_update.call_count == 1
        assert mock_msg_modify.call_count == 1
        modify_kwargs = mock_msg_modify.call_args[1]
        assert modify_kwargs["text"] == "Clarifying question answered."
        # Regression: `completedAt` must be an ISO-8601 string, not a raw
        # datetime — the wire serializer (``json.dumps``) can't encode
        # datetime and the backend rejected such bodies silently, leaving
        # the placeholder visually "running" in the chat UI.
        completed_at = modify_kwargs["completedAt"]
        assert isinstance(completed_at, str)
        assert completed_at.endswith("Z")

    @patch("unique_sdk.Message.modify")
    @patch("unique_sdk.MessageLog.update")
    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.Elicitation.respond_to_elicitation")
    def test_respond_no_cleanup_when_no_markers(
        self,
        mock_respond: MagicMock,
        mock_get: MagicMock,
        mock_log_update: MagicMock,
        mock_msg_modify: MagicMock,
    ) -> None:
        mock_respond.return_value = {"success": True}
        mock_get.return_value = _elicitation()  # no visibility metadata

        cmd_elicit_respond(
            _state(),
            "elicit_abc",
            action="ACCEPT",
            content='{"answer": "yes"}',
        )
        assert mock_log_update.call_count == 0
        assert mock_msg_modify.call_count == 0


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
