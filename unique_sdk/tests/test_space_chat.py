from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.api_resources._space import Space

CHAT_RESULT = {
    "id": "chat_1",
    "title": "Renamed chat",
    "createdAt": "2026-01-01T00:00:00.000Z",
    "object": "chat",
}


def test_update_chat_patches_space_chat_with_title() -> None:
    with patch.object(Space, "_static_request", return_value=CHAT_RESULT) as request:
        result = Space.update_chat(
            user_id="user_1",
            company_id="company_1",
            chat_id="chat_1",
            title="Renamed chat",
        )

    request.assert_called_once_with(
        "patch",
        "/space/chat/chat_1",
        "user_1",
        "company_1",
        params={"title": "Renamed chat"},
    )
    assert result == CHAT_RESULT


@pytest.mark.asyncio
async def test_update_chat_async_patches_space_chat_with_title() -> None:
    with patch.object(
        Space, "_static_request_async", new=AsyncMock(return_value=CHAT_RESULT)
    ) as request:
        result = await Space.update_chat_async(
            user_id="user_1",
            company_id="company_1",
            chat_id="chat_1",
            title="Renamed chat",
        )

    request.assert_awaited_once_with(
        "patch",
        "/space/chat/chat_1",
        "user_1",
        "company_1",
        params={"title": "Renamed chat"},
    )
    assert result == CHAT_RESULT
