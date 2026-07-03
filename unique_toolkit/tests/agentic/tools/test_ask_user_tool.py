"""Tests for the experimental AskUser (elicitation) tool."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from unique_toolkit.agentic.tools.experimental.ask_user_tool.config import (
    AskUserToolConfig,
)
from unique_toolkit.agentic.tools.experimental.ask_user_tool.tool import (
    AskUserTool,
    AskUserToolInput,
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.elicitation import (
    ElicitationDeclinedException,
    ElicitationExpiredException,
    ElicitationMode,
)
from unique_toolkit.language_model.schemas import LanguageModelFunction

_TOOL_PATH = "unique_toolkit.agentic.tools.experimental.ask_user_tool.tool"

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
        ('{"type": "object"}', False),  # a JSON string is not an object
        ("not json", False),
        ("[]", False),
        (123, False),
    ],
)
def test_input_response_schema_validation(raw: object, ok: bool) -> None:
    if ok:
        params = AskUserToolInput(message="Q", response_schema=raw)  # type: ignore[arg-type]
        assert isinstance(params.response_schema, dict)
    else:
        with pytest.raises(ValidationError):
            AskUserToolInput(message="Q", response_schema=raw)  # type: ignore[arg-type]


def test_input_strips_message() -> None:
    params = AskUserToolInput(
        message="  Which quarter?  ",
        response_schema=_MINIMAL_ANSWER_SCHEMA,
    )
    assert params.message == "Which quarter?"


def test_input_blank_message_rejected() -> None:
    with pytest.raises(ValidationError):
        AskUserToolInput(message="   ", response_schema=_MINIMAL_ANSWER_SCHEMA)


def test_parameter_descriptions_come_from_config() -> None:
    default_config = AskUserToolConfig()
    default_tool = AskUserTool(default_config, _chat_event())
    default_props = default_tool.tool_description_as_json()["properties"]
    assert default_props["message"]["description"] == default_config.message_description

    custom_tool = AskUserTool(
        AskUserToolConfig(message_description="custom"), _chat_event()
    )
    custom_props = custom_tool.tool_description_as_json()["properties"]
    assert custom_props["message"]["description"] == "custom"


def _make_ctx(chat_service: MagicMock) -> MagicMock:
    ctx = MagicMock()
    ctx.chat_service = chat_service
    return ctx


def _tool_with_service(
    config: AskUserToolConfig | None = None,
    *,
    wait_return: object = None,
    wait_side_effect: object = None,
) -> tuple[AskUserTool, MagicMock, MagicMock]:
    service = MagicMock()
    service.create_async = AsyncMock(return_value=SimpleNamespace(id="elic_1"))
    service.wait_for_response_async = AsyncMock(
        return_value=wait_return, side_effect=wait_side_effect
    )
    tool = AskUserTool(config or AskUserToolConfig(), _chat_event())
    ctx = _make_ctx(MagicMock(elicitation=service))
    return tool, service, ctx


@pytest.mark.asyncio
async def test_ask_user_success() -> None:
    tool, service, ctx = _tool_with_service(
        wait_return=SimpleNamespace(response_content={"answer": "Q1"})
    )

    resp = await tool.run(
        _tool_call(message="Which quarter?", response_schema=_MINIMAL_ANSWER_SCHEMA),
        ctx,
    )

    assert resp.error_message == ""
    assert json.loads(resp.content) == {"answer": "Q1"}

    create_kwargs = service.create_async.await_args.kwargs
    assert create_kwargs["mode"] == ElicitationMode.FORM
    assert create_kwargs["json_schema"] == _MINIMAL_ANSWER_SCHEMA
    assert create_kwargs["message"] == "Which quarter?"


@pytest.mark.asyncio
async def test_ask_user_confirm_schema_sent_to_platform() -> None:
    tool, service, ctx = _tool_with_service(
        wait_return=SimpleNamespace(response_content={"confirm": True})
    )

    await tool.run(
        _tool_call(
            message="Confirm permanent deletion?",
            response_schema=_MINIMAL_CONFIRM_SCHEMA,
        ),
        ctx,
    )

    assert (
        service.create_async.await_args.kwargs["json_schema"] == _MINIMAL_CONFIRM_SCHEMA
    )


@pytest.mark.asyncio
async def test_ask_user_missing_response_schema_raises() -> None:
    tool = AskUserTool(AskUserToolConfig(), _chat_event())
    with pytest.raises(ValidationError):
        await tool.run(_tool_call(message="Which quarter?"), MagicMock())


@pytest.mark.asyncio
async def test_ask_user_empty_message_raises() -> None:
    tool = AskUserTool(AskUserToolConfig(), _chat_event())
    with pytest.raises(ValidationError):
        await tool.run(
            _tool_call(message="  ", response_schema=_MINIMAL_ANSWER_SCHEMA),
            MagicMock(),
        )


@pytest.mark.asyncio
async def test_ask_user_declined_returns_configured_message() -> None:
    config = AskUserToolConfig(declined_message="custom declined")
    tool, _, ctx = _tool_with_service(
        config, wait_side_effect=ElicitationDeclinedException()
    )

    resp = await tool.run(
        _tool_call(message="Sure?", response_schema=_MINIMAL_ANSWER_SCHEMA), ctx
    )

    assert resp.error_message == ""
    assert resp.content == "custom declined"


@pytest.mark.asyncio
async def test_ask_user_expired_returns_default_message() -> None:
    tool, _, ctx = _tool_with_service(wait_side_effect=ElicitationExpiredException())

    resp = await tool.run(
        _tool_call(message="Slow user", response_schema=_MINIMAL_ANSWER_SCHEMA), ctx
    )

    assert resp.error_message == ""
    assert resp.content == AskUserToolConfig().expired_message


@pytest.mark.asyncio
async def test_ask_user_cancelled_returns_configured_message() -> None:
    from unique_toolkit.elicitation import ElicitationCancelledException

    config = AskUserToolConfig(cancelled_message="custom cancelled")
    tool, _, ctx = _tool_with_service(
        config, wait_side_effect=ElicitationCancelledException()
    )

    resp = await tool.run(
        _tool_call(message="Sure?", response_schema=_MINIMAL_ANSWER_SCHEMA), ctx
    )

    assert resp.error_message == ""
    assert resp.content == "custom cancelled"


def test_ask_user_does_not_take_control() -> None:
    event = _chat_event()
    tool = AskUserTool(AskUserToolConfig(), event)
    assert tool.takes_control() is False
