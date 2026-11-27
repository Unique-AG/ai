from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk import ChatCompletion


@pytest.mark.ai
def test_create_forwards_supplied_headers_separately_from_json_params() -> None:
    """Purpose: Verify sync completion headers use the HTTP header channel.
    Why this matters: Attribution IDs must not leak into the JSON request body.
    Setup summary: Call create with headers and assert the resource request arguments.
    """
    headers = {"x-chat-id": "chat_1", "x-assistant-id": "assistant_1"}

    with patch.object(
        ChatCompletion,
        "_static_request",
        return_value={},
    ) as request:
        ChatCompletion.create(
            company_id="company_1",
            user_id="user_1",
            headers=headers,
            messages=[],
        )

    request.assert_called_once_with(
        "post",
        "/openai/chat/completions",
        company_id="company_1",
        user_id="user_1",
        params={"messages": []},
        supplied_headers=headers,
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_async_forwards_supplied_headers_separately_from_json_params() -> (
    None
):
    """Purpose: Verify async completion headers use the HTTP header channel.
    Why this matters: Async attribution IDs must not leak into the JSON request body.
    Setup summary: Call create_async with headers and assert resource request arguments.
    """
    headers = {"x-chat-id": "chat_1", "x-assistant-id": "assistant_1"}

    with patch.object(
        ChatCompletion,
        "_static_request_async",
        AsyncMock(return_value={}),
    ) as request:
        await ChatCompletion.create_async(
            company_id="company_1",
            user_id="user_1",
            headers=headers,
            messages=[],
        )

    request.assert_awaited_once_with(
        "post",
        "/openai/chat/completions",
        company_id="company_1",
        user_id="user_1",
        params={"messages": []},
        supplied_headers=headers,
    )
