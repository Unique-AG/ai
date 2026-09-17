"""Tests for ChatService.mark_turn_system_interrupted_async (UN-24137).

Covers:
- The ChatService method anchors on the current context's originating USER message
- The fixed SYSTEM_INTERRUPTED reason is enforced at the SDK layer (no reason
  parameter exists on the toolkit surface)
- Repeated calls succeed (server-side idempotency passes through)
- MessageLogStatus.CANCELLED exists alongside FAILED
"""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueContext,
)
from unique_toolkit.chat.schemas import ChatMessageRole, MessageLogStatus
from unique_toolkit.services.chat_service import ChatService

_USER_ID = "user-1"
_COMPANY_ID = "company-1"
_CHAT_ID = "chat-1"
_USER_MESSAGE_ID = "umsg-1"
_ASSISTANT_MESSAGE_ID = "amsg-1"


@pytest.fixture
def chat_service() -> ChatService:
    auth = AuthContext(user_id=SecretStr(_USER_ID), company_id=SecretStr(_COMPANY_ID))
    chat = ChatContext(
        chat_id=_CHAT_ID,
        assistant_id="assistant-1",
        last_assistant_message_id=_ASSISTANT_MESSAGE_ID,
        last_user_message_id=_USER_MESSAGE_ID,
        last_user_message_text="hello",
    )
    return ChatService.from_context(UniqueContext(auth=auth, chat=chat))


def _sdk_message_payload() -> dict:
    return {
        "id": _USER_MESSAGE_ID,
        "chatId": _CHAT_ID,
        "role": "USER",
        "text": "hello",
    }


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.mark_turn_system_interrupted_async", new_callable=AsyncMock)
async def test_mark_turn_system_interrupted__targets_originating_user_message(
    mock_sdk: AsyncMock, chat_service: ChatService
):
    """Purpose: The method anchors on the chat context's originating USER message.

    Why this matters: The turn interruption marker must land on the USER turn
    anchor, not the assistant message, and the caller must not be able to pick
    a different message (no message_id parameter).
    Setup summary: Patch the SDK call, invoke the ChatService method, and assert
    it was called once with the context's user message id and chat id.
    """
    mock_sdk.return_value = _sdk_message_payload()

    message = await chat_service.mark_turn_system_interrupted_async()

    mock_sdk.assert_called_once_with(
        user_id=_USER_ID,
        company_id=_COMPANY_ID,
        id=_USER_MESSAGE_ID,
        chatId=_CHAT_ID,
    )
    assert message.id == _USER_MESSAGE_ID
    assert message.role == ChatMessageRole.USER


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.mark_turn_system_interrupted_async", new_callable=AsyncMock)
async def test_mark_turn_system_interrupted__repeated_calls_succeed(
    mock_sdk: AsyncMock, chat_service: ChatService
):
    """Purpose: Calling the method twice raises nothing and returns both times.

    Why this matters: The server endpoint is idempotent (returns 200 with the
    unchanged message on repeat calls and on a lost race against user Stop);
    the toolkit must pass that through without client-side state or errors.
    Setup summary: Patch the SDK call to return the same payload twice, call
    the method twice, and assert two successful SDK invocations.
    """
    mock_sdk.return_value = _sdk_message_payload()

    first = await chat_service.mark_turn_system_interrupted_async()
    second = await chat_service.mark_turn_system_interrupted_async()

    assert mock_sdk.call_count == 2
    assert first.id == second.id == _USER_MESSAGE_ID


@pytest.mark.ai
@pytest.mark.asyncio
@patch("unique_sdk.Message.mark_turn_system_interrupted_async", new_callable=AsyncMock)
async def test_mark_turn_system_interrupted__propagates_transport_errors(
    mock_sdk: AsyncMock, chat_service: ChatService
):
    """Purpose: Transport failures surface to the caller instead of being swallowed.

    Why this matters: Conduct invokes this from failure-handling paths and
    decides itself whether to treat it as best-effort; silent failure here
    would hide a missing interruption marker.
    Setup summary: Patch the SDK call to raise and assert the exception
    propagates from the ChatService method.
    """
    mock_sdk.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await chat_service.mark_turn_system_interrupted_async()


@pytest.mark.ai
def test_message_log_status__has_cancelled__distinct_from_failed():
    """Purpose: MessageLogStatus gains CANCELLED without touching existing members.

    Why this matters: Conduct closes in-flight thinking/tool steps with
    CANCELLED when the user pressed Stop; FAILED stays reserved for
    system-side interruption. Existing values must be untouched for
    backward compatibility with persisted logs.
    Setup summary: Assert the CANCELLED value and the full member set.
    """
    assert MessageLogStatus.CANCELLED == "CANCELLED"
    assert {status.value for status in MessageLogStatus} == {
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
    }
