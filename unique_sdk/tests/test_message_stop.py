"""Tests for Message.stop(_async) (UN-30319)."""

from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.api_resources._message import Message

_USER_ID = "user-1"
_COMPANY_ID = "company-1"
_USER_MESSAGE_ID = "umsg-1"
_CHAT_ID = "chat-1"


@pytest.mark.ai
def test_stop__posts_chat_id__to_stop_endpoint():
    """Purpose: The sync variant POSTs to /messages/{id}/stop with the chat id.

    Why this matters: This is the stop a user triggers in the chat. A wrong
    route or body leaves an unwatched turn running.
    Setup summary: Patch _static_request, call stop, assert method, URL, params.
    """
    with patch.object(Message, "_static_request") as mock_request:
        mock_request.return_value = Message.construct_from(
            {"id": _USER_MESSAGE_ID}, _USER_ID, _COMPANY_ID
        )

        Message.stop(_USER_ID, _COMPANY_ID, _USER_MESSAGE_ID, chatId=_CHAT_ID)

    mock_request.assert_called_once_with(
        "post",
        f"/messages/{_USER_MESSAGE_ID}/stop",
        _USER_ID,
        _COMPANY_ID,
        {"chatId": _CHAT_ID},
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_stop_async__posts_chat_id__to_stop_endpoint():
    """Purpose: The async variant POSTs to /messages/{id}/stop with the chat id.

    Why this matters: The abandoned-wait path calls the async variant.
    Setup summary: Patch _static_request_async, call stop_async, assert the call.
    """
    with patch.object(
        Message, "_static_request_async", new_callable=AsyncMock
    ) as mock_request:
        mock_request.return_value = Message.construct_from(
            {"id": _USER_MESSAGE_ID}, _USER_ID, _COMPANY_ID
        )

        await Message.stop_async(
            _USER_ID, _COMPANY_ID, _USER_MESSAGE_ID, chatId=_CHAT_ID
        )

    mock_request.assert_called_once_with(
        "post",
        f"/messages/{_USER_MESSAGE_ID}/stop",
        _USER_ID,
        _COMPANY_ID,
        {"chatId": _CHAT_ID},
    )
