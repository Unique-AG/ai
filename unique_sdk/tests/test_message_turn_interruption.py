"""Tests for Message.mark_turn_system_interrupted(_async) (UN-24137).

Conforms to unique_skills/.claude/skills/python-testing (naming, docstrings, ai mark).
"""

from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.api_resources._message import Message

_USER_ID = "user-1"
_COMPANY_ID = "company-1"
_USER_MESSAGE_ID = "umsg-1"
_CHAT_ID = "chat-1"


@pytest.mark.ai
def test_mark_turn_system_interrupted__posts_fixed_reason__to_dedicated_endpoint():
    """Purpose: The sync variant POSTs to /messages/{id}/turn-interruption with a fixed reason.

    Why this matters: The SYSTEM_INTERRUPTED marker must be service-authored via a
    dedicated endpoint; the reason must not be caller-controlled, so the SDK
    hardcodes it (UN-24137).
    Setup summary: Patch _static_request, call mark_turn_system_interrupted, and
    assert the method, URL, and params (chatId plus hardcoded reason).
    """
    with patch.object(Message, "_static_request") as mock_request:
        mock_request.return_value = Message.construct_from(
            {"id": _USER_MESSAGE_ID}, _USER_ID, _COMPANY_ID
        )

        Message.mark_turn_system_interrupted(
            _USER_ID, _COMPANY_ID, _USER_MESSAGE_ID, chatId=_CHAT_ID
        )

    mock_request.assert_called_once_with(
        "post",
        f"/messages/{_USER_MESSAGE_ID}/turn-interruption",
        _USER_ID,
        _COMPANY_ID,
        {"chatId": _CHAT_ID, "reason": "SYSTEM_INTERRUPTED"},
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_mark_turn_system_interrupted_async__posts_fixed_reason__to_dedicated_endpoint():
    """Purpose: The async variant POSTs to /messages/{id}/turn-interruption with a fixed reason.

    Why this matters: Conduct calls the async path from failure handling; it must
    hit the service-authenticated endpoint with the server-defined reason only.
    Setup summary: Patch _static_request_async, call mark_turn_system_interrupted_async,
    and assert the method, URL, and params (chatId plus hardcoded reason).
    """
    with patch.object(
        Message, "_static_request_async", new_callable=AsyncMock
    ) as mock_request:
        mock_request.return_value = Message.construct_from(
            {"id": _USER_MESSAGE_ID}, _USER_ID, _COMPANY_ID
        )

        await Message.mark_turn_system_interrupted_async(
            _USER_ID, _COMPANY_ID, _USER_MESSAGE_ID, chatId=_CHAT_ID
        )

    mock_request.assert_called_once_with(
        "post",
        f"/messages/{_USER_MESSAGE_ID}/turn-interruption",
        _USER_ID,
        _COMPANY_ID,
        {"chatId": _CHAT_ID, "reason": "SYSTEM_INTERRUPTED"},
    )


@pytest.mark.ai
def test_mark_turn_system_interrupted__url_encodes_message_id():
    """Purpose: Message IDs are URL-quoted when building the endpoint path.

    Why this matters: Prevents path injection or malformed URLs for IDs with
    reserved characters, matching modify/delete behavior on this resource.
    Setup summary: Call with an ID containing a slash and assert the quoted path.
    """
    with patch.object(Message, "_static_request") as mock_request:
        mock_request.return_value = Message.construct_from(
            {"id": "a/b"}, _USER_ID, _COMPANY_ID
        )

        Message.mark_turn_system_interrupted(
            _USER_ID, _COMPANY_ID, "a/b", chatId=_CHAT_ID
        )

    assert mock_request.call_args[0][1] == "/messages/a%2Fb/turn-interruption"
