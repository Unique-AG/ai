from unittest.mock import AsyncMock, patch

import pytest

from unique_sdk.api_resources._content import Content

pytestmark = pytest.mark.ai

USER_ID = "user_1"
COMPANY_ID = "company_1"
CONTENT_ID = "cont_1"
CHAT_ID = "chat_1"


def test_update_ingestion_state_serializes_chat_id() -> None:
    with patch.object(Content, "_static_request") as mock_request:
        Content.update_ingestion_state(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            contentId=CONTENT_ID,
            ingestionState="QUEUED",
            chatId=CHAT_ID,
        )

        mock_request.assert_called_once_with(
            "patch",
            f"/content/{CONTENT_ID}/ingestion-state",
            USER_ID,
            COMPANY_ID,
            params={"ingestionState": "QUEUED", "chatId": CHAT_ID},
        )


def test_update_ingestion_state_omits_chat_id_when_not_provided() -> None:
    with patch.object(Content, "_static_request") as mock_request:
        Content.update_ingestion_state(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            contentId=CONTENT_ID,
            ingestionState="QUEUED",
        )

        mock_request.assert_called_once_with(
            "patch",
            f"/content/{CONTENT_ID}/ingestion-state",
            USER_ID,
            COMPANY_ID,
            params={"ingestionState": "QUEUED"},
        )


@pytest.mark.asyncio
async def test_update_ingestion_state_async_serializes_chat_id() -> None:
    with patch.object(
        Content, "_static_request_async", new_callable=AsyncMock
    ) as mock_request:
        await Content.update_ingestion_state_async(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            contentId=CONTENT_ID,
            ingestionState="QUEUED",
            chatId=CHAT_ID,
        )

        mock_request.assert_awaited_once_with(
            "patch",
            f"/content/{CONTENT_ID}/ingestion-state",
            USER_ID,
            COMPANY_ID,
            params={"ingestionState": "QUEUED", "chatId": CHAT_ID},
        )


@pytest.mark.asyncio
async def test_update_ingestion_state_async_omits_chat_id_when_not_provided() -> None:
    with patch.object(
        Content, "_static_request_async", new_callable=AsyncMock
    ) as mock_request:
        await Content.update_ingestion_state_async(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            contentId=CONTENT_ID,
            ingestionState="QUEUED",
        )

        mock_request.assert_awaited_once_with(
            "patch",
            f"/content/{CONTENT_ID}/ingestion-state",
            USER_ID,
            COMPANY_ID,
            params={"ingestionState": "QUEUED"},
        )
