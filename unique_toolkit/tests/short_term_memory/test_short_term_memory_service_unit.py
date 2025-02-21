import json
from unittest.mock import patch

import pytest
from unique_sdk import ShortTermMemory as ShortTermMemoryAPI

from unique_toolkit.short_term_memory.service import ShortTermMemoryService


@pytest.mark.asyncio
@patch.object(ShortTermMemoryAPI, "create_async")
async def test_setter(mock_create):
    mock_create.return_value = {
        "id": "123",
        "object": "test",
        "chatId": "chat_234234asdf",
        "messageId": None,
        "data": "value",
    }

    stm_service = ShortTermMemoryService(
        user_id="123", company_id="456", chat_id="789", message_id="101112"
    )

    # Mock unique_sdk.api_resources._short_term_memory.ShortTermMemoryAPI.find_latest_async
    await stm_service.set("test", value="value")
    mock_create.assert_called_once_with(
        user_id="123",
        company_id="456",
        memoryName="test",
        chatId="789",
        messageId="101112",
        data="value",
    )


@pytest.mark.asyncio
@patch.object(ShortTermMemoryAPI, "create_async")
async def test_setter_with_dict(mock_create):
    val = {"key1": "value1", "key2": "value2"}
    str_val = json.dumps({"key1": "value1", "key2": "value2"})
    mock_create.return_value = {
        "id": "123",
        "object": "test",
        "chatId": "chat_234234asdf",
        "messageId": None,
        "data": str_val,
    }

    stm_service = ShortTermMemoryService(
        user_id="123", company_id="456", chat_id="789", message_id="101112"
    )
    await stm_service.set("test", value=val)
    mock_create.assert_called_once_with(
        user_id="123",
        company_id="456",
        memoryName="test",
        chatId="789",
        messageId="101112",
        data=str_val,
    )
