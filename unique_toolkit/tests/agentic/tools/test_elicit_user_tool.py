"""Tests for the experimental AskUser (elicitation) tool."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import unique_sdk

from unique_toolkit.agentic.tools.experimental.elicit_user_tool.config import (
    ElicitUserToolConfig,
)
from unique_toolkit.agentic.tools.experimental.elicit_user_tool.tool import (
    ElicitUserTool,
    _parse_response_schema,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import LanguageModelFunction

_TOOL_PATH = "unique_toolkit.agentic.tools.experimental.elicit_user_tool.tool"

_MINIMAL_ANSWER_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "Free-text answer to the question.",
        },
    },
    "required": ["answer"],
}

_MINIMAL_CONFIRM_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "confirm": {"type": "boolean", "description": "Acknowledge destructive action"},
    },
    "required": ["confirm"],
}


def _chat_event() -> ChatEvent:
    return ChatEvent.model_validate(
        {
            "id": "evt_1",
            "event": "unique.chat.user-message.created",
            "user_id": "user_1",
            "company_id": "company_1",
            "payload": {
                "name": "test",
                "description": "",
                "configuration": {},
                "chat_id": "chat_1",
                "assistant_id": "asst_1",
                "user_message": {
                    "id": "usr_msg_1",
                    "text": "hi",
                    "original_text": "hi",
                    "created_at": "2026-01-01T00:00:00Z",
                    "language": "en",
                },
                "assistant_message": {
                    "id": "asst_msg_1",
                    "created_at": "2026-01-01T00:00:01Z",
                },
            },
        }
    )


def _tool_call(**arguments: object) -> LanguageModelFunction:
    tc = MagicMock(spec=LanguageModelFunction)
    tc.id = "call_1"
    tc.arguments = arguments
    return tc


@pytest.mark.parametrize(
    ("raw", "ok"),
    [
        (None, False),
        ({"type": "object", "properties": {"x": {"type": "string"}}}, True),
        ('{"type": "object"}', True),
        ("not json", False),
        ("[]", False),
        (123, False),
    ],
)
def test_parse_response_schema(raw: object, ok: bool) -> None:
    schema, err = _parse_response_schema(raw)
    if ok:
        assert err is None
        assert schema is not None
        assert isinstance(schema, dict)
    else:
        assert err is not None
        assert schema is None


@pytest.mark.asyncio
async def test_ask_user_success() -> None:
    event = _chat_event()
    tool = ElicitUserTool(ElicitUserToolConfig(), event)

    pending = {"id": "elic_1", "status": "PENDING"}
    answered = {
        "id": "elic_1",
        "status": "RESPONDED",
        "responseContent": {"answer": "Q1"},
    }

    create_elicitation = AsyncMock(return_value=pending)
    with (
        patch.object(
            unique_sdk.Elicitation, "create_elicitation_async", create_elicitation
        ),
        patch.object(
            unique_sdk.Elicitation,
            "get_elicitation_async",
            new_callable=AsyncMock,
            side_effect=[pending, answered],
        ),
        patch(f"{_TOOL_PATH}.asyncio.sleep", new_callable=AsyncMock),
    ):
        resp = await tool.run(
            _tool_call(message="Which quarter?", response_schema=_MINIMAL_ANSWER_SCHEMA)
        )

    assert create_elicitation.await_count == 1
    sent_schema = create_elicitation.await_args.kwargs["schema"]
    assert "answer" in sent_schema["properties"]

    assert resp.error_message == ""
    body = json.loads(resp.content)
    assert body["elicitation_id"] == "elic_1"
    assert body["status"] == "RESPONDED"
    assert body["response"] == {"answer": "Q1"}
    assert body["timed_out"] is False
    assert resp.system_reminder == ""


@pytest.mark.asyncio
async def test_ask_user_missing_response_schema_errors() -> None:
    event = _chat_event()
    tool = ElicitUserTool(ElicitUserToolConfig(), event)
    resp = await tool.run(_tool_call(message="Which quarter?"))
    assert resp.error_message != ""
    assert "response_schema" in resp.error_message.lower()


@pytest.mark.asyncio
async def test_ask_user_confirm_schema_sent_to_platform() -> None:
    event = _chat_event()
    tool = ElicitUserTool(ElicitUserToolConfig(), event)

    pending = {"id": "elic_1", "status": "PENDING"}
    answered = {
        "id": "elic_1",
        "status": "RESPONDED",
        "responseContent": {"confirm": True},
    }

    create_elicitation = AsyncMock(return_value=pending)
    with (
        patch.object(
            unique_sdk.Elicitation, "create_elicitation_async", create_elicitation
        ),
        patch.object(
            unique_sdk.Elicitation,
            "get_elicitation_async",
            new_callable=AsyncMock,
            side_effect=[pending, answered],
        ),
        patch(f"{_TOOL_PATH}.asyncio.sleep", new_callable=AsyncMock),
    ):
        resp = await tool.run(
            _tool_call(
                message="Confirm you want to permanently delete everything in this workspace?",
                response_schema=_MINIMAL_CONFIRM_SCHEMA,
            )
        )

    assert resp.error_message == ""
    schema = create_elicitation.await_args.kwargs["schema"]
    assert schema["properties"]["confirm"]["type"] == "boolean"


@pytest.mark.asyncio
async def test_ask_user_empty_message_errors() -> None:
    event = _chat_event()
    tool = ElicitUserTool(ElicitUserToolConfig(), event)
    resp = await tool.run(
        _tool_call(message="  ", response_schema=_MINIMAL_ANSWER_SCHEMA)
    )
    assert resp.error_message != ""


@pytest.mark.asyncio
async def test_ask_user_create_api_error() -> None:
    event = _chat_event()
    tool = ElicitUserTool(ElicitUserToolConfig(), event)

    with patch.object(
        unique_sdk.Elicitation,
        "create_elicitation_async",
        new_callable=AsyncMock,
        side_effect=unique_sdk.APIError("boom", http_status=500, http_body=None),
    ):
        resp = await tool.run(
            _tool_call(message="Hello?", response_schema=_MINIMAL_ANSWER_SCHEMA)
        )

    assert "Failed to create elicitation" in resp.error_message


@pytest.mark.asyncio
async def test_ask_user_times_out() -> None:
    event = _chat_event()
    tool = ElicitUserTool(
        ElicitUserToolConfig(timeout_seconds=2, poll_interval_seconds=0.5),
        event,
    )

    pending = {"id": "elic_1", "status": "PENDING"}

    loop_mock = MagicMock()
    loop_mock.time.side_effect = [0.0, 0.0, 2.0]

    with (
        patch.object(
            unique_sdk.Elicitation,
            "create_elicitation_async",
            new_callable=AsyncMock,
            return_value=pending,
        ),
        patch.object(
            unique_sdk.Elicitation,
            "get_elicitation_async",
            new_callable=AsyncMock,
            return_value=pending,
        ),
        patch(f"{_TOOL_PATH}.asyncio.get_running_loop", return_value=loop_mock),
        patch(f"{_TOOL_PATH}.asyncio.sleep", new_callable=AsyncMock),
    ):
        resp = await tool.run(
            _tool_call(message="Slow user", response_schema=_MINIMAL_ANSWER_SCHEMA)
        )

    assert resp.error_message == ""
    body = json.loads(resp.content)
    assert body["timed_out"] is True
    assert "timed out" in resp.system_reminder.lower()


@pytest.mark.asyncio
async def test_ask_user_declined_sets_reminder() -> None:
    event = _chat_event()
    tool = ElicitUserTool(ElicitUserToolConfig(), event)

    pending = {"id": "elic_1", "status": "PENDING"}
    declined = {"id": "elic_1", "status": "DECLINED", "responseContent": None}

    with (
        patch.object(
            unique_sdk.Elicitation,
            "create_elicitation_async",
            new_callable=AsyncMock,
            return_value=pending,
        ),
        patch.object(
            unique_sdk.Elicitation,
            "get_elicitation_async",
            new_callable=AsyncMock,
            side_effect=[declined],
        ),
        patch(f"{_TOOL_PATH}.asyncio.sleep", new_callable=AsyncMock),
    ):
        resp = await tool.run(
            _tool_call(message="Sure?", response_schema=_MINIMAL_ANSWER_SCHEMA)
        )

    assert resp.error_message == ""
    assert "did not complete" in resp.system_reminder.lower()


def test_ask_user_does_not_take_control() -> None:
    event = _chat_event()
    tool = ElicitUserTool(ElicitUserToolConfig(), event)
    assert tool.takes_control() is False
