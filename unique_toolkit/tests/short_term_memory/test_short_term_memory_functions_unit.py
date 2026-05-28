from unittest.mock import patch

import pytest
from unique_sdk import ShortTermMemory as ShortTermMemoryAPI

from unique_toolkit.short_term_memory.functions import (
    find_last_chat_memory,
    find_last_chat_memory_async,
    find_last_message_memory,
    find_last_message_memory_async,
    find_latest_memory,
    find_latest_memory_async,
)

_VALID_STM = {
    "id": "mem_123",
    "object": "my-key",
    "chatId": "chat_abc",
    "messageId": None,
    "data": "hello",
}


# --- empty-response returns None ---


@pytest.mark.asyncio
@patch.object(ShortTermMemoryAPI, "find_latest_async", return_value={})
async def test_find_latest_memory_async_returns_none_on_empty(mock_find):
    result = await find_latest_memory_async(
        user_id="u", company_id="c", key="k", chat_id="chat_1"
    )
    assert result is None


@patch.object(ShortTermMemoryAPI, "find_latest", return_value={})
def test_find_latest_memory_returns_none_on_empty(mock_find):
    result = find_latest_memory(user_id="u", company_id="c", key="k", chat_id="chat_1")
    assert result is None


@patch.object(ShortTermMemoryAPI, "find_latest", return_value={})
def test_find_last_chat_memory_returns_none_on_empty(mock_find):
    result = find_last_chat_memory(
        user_id="u", company_id="c", key="k", chat_id="chat_1"
    )
    assert result is None


@pytest.mark.asyncio
@patch.object(ShortTermMemoryAPI, "find_latest_async", return_value={})
async def test_find_last_chat_memory_async_returns_none_on_empty(mock_find):
    result = await find_last_chat_memory_async(
        user_id="u", company_id="c", key="k", chat_id="chat_1"
    )
    assert result is None


@patch.object(ShortTermMemoryAPI, "find_latest", return_value={})
def test_find_last_message_memory_returns_none_on_empty(mock_find):
    result = find_last_message_memory(
        user_id="u", company_id="c", key="k", message_id="msg_1"
    )
    assert result is None


@pytest.mark.asyncio
@patch.object(ShortTermMemoryAPI, "find_latest_async", return_value={})
async def test_find_last_message_memory_async_returns_none_on_empty(mock_find):
    result = await find_last_message_memory_async(
        user_id="u", company_id="c", key="k", message_id="msg_1"
    )
    assert result is None


# --- valid response is parsed correctly ---


@pytest.mark.asyncio
@patch.object(ShortTermMemoryAPI, "find_latest_async", return_value=_VALID_STM)
async def test_find_latest_memory_async_returns_model_on_valid(mock_find):
    result = await find_latest_memory_async(
        user_id="u", company_id="c", key="my-key", chat_id="chat_abc"
    )
    assert result is not None
    assert result.id == "mem_123"
    assert result.key == "my-key"


@patch.object(ShortTermMemoryAPI, "find_latest", return_value=_VALID_STM)
def test_find_latest_memory_returns_model_on_valid(mock_find):
    result = find_latest_memory(
        user_id="u", company_id="c", key="my-key", chat_id="chat_abc"
    )
    assert result is not None
    assert result.id == "mem_123"
