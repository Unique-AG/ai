"""Tests for ToolCall API resource and helpers."""

from unittest.mock import patch

import pytest

from unique_sdk._list_object import ListObject
from unique_sdk.api_resources._tool_call import (
    MESSAGE_IDS_PAGE_SIZE,
    ToolCall,
    _chunk_message_ids,
)

# --- _chunk_message_ids ---


def test_chunk_message_ids_empty_string():
    assert _chunk_message_ids("") == []


def test_chunk_message_ids_whitespace_only():
    assert _chunk_message_ids("  ,  ,  ") == []


def test_chunk_message_ids_single_id():
    assert _chunk_message_ids("msg-1") == ["msg-1"]


def test_chunk_message_ids_strips_whitespace():
    assert _chunk_message_ids(" msg-1 , msg-2 ") == ["msg-1,msg-2"]


def test_chunk_message_ids_at_page_boundary():
    ids = [f"m{i}" for i in range(MESSAGE_IDS_PAGE_SIZE)]
    chunks = _chunk_message_ids(",".join(ids))
    assert len(chunks) == 1
    assert chunks[0].count(",") == MESSAGE_IDS_PAGE_SIZE - 1


def test_chunk_message_ids_over_page_boundary():
    ids = [f"m{i}" for i in range(MESSAGE_IDS_PAGE_SIZE + 1)]
    chunks = _chunk_message_ids(",".join(ids))
    assert len(chunks) == 2
    assert chunks[0].count(",") == MESSAGE_IDS_PAGE_SIZE - 1
    assert chunks[1] == f"m{MESSAGE_IDS_PAGE_SIZE}"


def test_chunk_message_ids_two_full_pages():
    ids = [f"m{i}" for i in range(MESSAGE_IDS_PAGE_SIZE * 2)]
    chunks = _chunk_message_ids(",".join(ids))
    assert len(chunks) == 2
    assert all(c.count(",") == MESSAGE_IDS_PAGE_SIZE - 1 for c in chunks)


# --- ToolCall class methods (mocked) ---


def _make_list_object(data=None):
    if data is None:
        data = []
    return ListObject.construct_from(
        {"data": data, "has_more": False, "url": "/messages/tools"},
        user_id="u",
        company_id="c",
        last_response=None,
    )


@patch.object(ToolCall, "_static_request")
def test_create_many_returns_list_object(mock_request):
    mock_request.return_value = _make_list_object([{"id": "tc-1"}])
    result = ToolCall.create_many("user", "company", messageId="msg-1", tools=[])
    assert isinstance(result, ListObject)
    assert result.get("data") == [{"id": "tc-1"}]
    mock_request.assert_called_once_with(
        "post",
        "/messages/tools",
        "user",
        "company",
        params={"messageId": "msg-1", "tools": []},
    )


@patch.object(ToolCall, "_static_request")
def test_list_returns_list_object(mock_request):
    mock_request.return_value = _make_list_object([])
    result = ToolCall.list("user", "company", messageIds="msg-1,msg-2")
    assert isinstance(result, ListObject)
    mock_request.assert_called_once_with(
        "get",
        "/messages/tools",
        "user",
        "company",
        params={"messageIds": "msg-1,msg-2"},
    )


@patch.object(ToolCall, "_static_request")
def test_list_by_message_ids_empty_returns_empty_list(mock_request):
    result = ToolCall.list_by_message_ids("user", "company", messageIds="")
    assert isinstance(result, ListObject)
    assert result.get("data") == []
    mock_request.assert_not_called()


@patch.object(ToolCall, "_static_request")
def test_list_by_message_ids_single_chunk_calls_once(mock_request):
    mock_request.return_value = _make_list_object([{"id": "tc-1"}])
    result = ToolCall.list_by_message_ids("user", "company", messageIds="msg-1")
    assert len(result.get("data", [])) == 1
    mock_request.assert_called_once_with(
        "get", "/messages/tools", "user", "company", params={"messageIds": "msg-1"}
    )


@patch.object(ToolCall, "_static_request")
def test_list_by_message_ids_multiple_chunks_merges_data(mock_request):
    ids = [f"m{i}" for i in range(MESSAGE_IDS_PAGE_SIZE + 10)]
    msg_ids_str = ",".join(ids)
    mock_request.side_effect = [
        _make_list_object([{"id": "page1"}]),
        _make_list_object([{"id": "page2"}]),
    ]
    result = ToolCall.list_by_message_ids("user", "company", messageIds=msg_ids_str)
    assert result.get("data") == [{"id": "page1"}, {"id": "page2"}]
    assert mock_request.call_count == 2


@pytest.mark.asyncio
@patch.object(ToolCall, "_static_request_async")
async def test_create_many_async_returns_list_object(mock_request):
    mock_request.return_value = _make_list_object([])
    result = await ToolCall.create_many_async(
        "user", "company", messageId="msg-1", tools=[]
    )
    assert isinstance(result, ListObject)
    mock_request.assert_called_once()


@pytest.mark.asyncio
@patch.object(ToolCall, "_static_request_async")
async def test_list_by_message_ids_async_empty_returns_empty_list(mock_request):
    result = await ToolCall.list_by_message_ids_async("user", "company", messageIds="")
    assert isinstance(result, ListObject)
    assert result.get("data") == []
    mock_request.assert_not_called()


@pytest.mark.asyncio
@patch.object(ToolCall, "_static_request_async")
async def test_list_by_message_ids_async_multiple_chunks_merges_data(mock_request):
    ids = [f"m{i}" for i in range(MESSAGE_IDS_PAGE_SIZE + 10)]
    msg_ids_str = ",".join(ids)
    mock_request.side_effect = [
        _make_list_object([{"id": "a"}]),
        _make_list_object([{"id": "b"}]),
    ]
    result = await ToolCall.list_by_message_ids_async(
        "user", "company", messageIds=msg_ids_str
    )
    assert result.get("data") == [{"id": "a"}, {"id": "b"}]
    assert mock_request.call_count == 2
