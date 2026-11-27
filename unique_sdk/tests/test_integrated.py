from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk import Integrated


@pytest.mark.ai
@pytest.mark.asyncio
async def test_count_tokens_async__uses_authenticated_anthropic_proxy_AI() -> None:
    """
    Purpose: Verify provider token counting uses the public proxy with user and company context.
    Why this matters: The counter must reuse platform authentication instead of accessing provider credentials.
    Setup summary: One model request -> proxy endpoint with the unchanged count payload.
    """
    payload = {
        "model": "litellm:claude-sonnet-5-5",
        "system": "You are helpful.",
        "messages": [{"role": "user", "content": "Hello"}],
        "tools": [
            {
                "name": "search",
                "description": "Search",
                "input_schema": {"type": "object", "properties": {}},
            }
        ],
    }

    with patch.object(
        Integrated,
        "_static_request_async",
        AsyncMock(return_value={"input_tokens": 42}),
    ) as request:
        result = await Integrated.count_tokens_async(
            user_id="user_1",
            company_id="company_1",
            **payload,  # type: ignore[arg-type]
        )

    assert result == {"input_tokens": 42}
    request.assert_awaited_once_with(
        "post",
        "/anthropic-proxy/v1/messages/count_tokens",
        "user_1",
        "company_1",
        payload,
    )
