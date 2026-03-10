"""Tests for ToolCall API resource and helpers.

Conforms to unique_skills/.claude/skills/python-testing (naming, docstrings, mocker, ai mark).
"""

import pytest

from unique_sdk._list_object import ListObject
from unique_sdk.api_resources._tool_call import (
    MESSAGE_IDS_PAGE_SIZE,
    ToolCall,
    _chunk_message_ids,
)


def _make_list_object(data=None):
    """Build a ListObject like the API returns (for mocks)."""
    if data is None:
        data = []
    return ListObject.construct_from(
        {"data": data, "has_more": False, "url": "/messages/tools"},
        user_id="u",
        company_id="c",
        last_response=None,
    )


# --- _chunk_message_ids ---


@pytest.mark.ai
def test_chunk_message_ids__empty_input__returns_empty_list():
    """Purpose: Empty string produces no chunks.

    Why this matters: Callers must get [] when there are no message IDs so list_by_message_ids
    can return early without calling the API.
    Setup summary: Call _chunk_message_ids(""). Assert result is [].
    """
    assert _chunk_message_ids("") == []


@pytest.mark.ai
def test_chunk_message_ids__whitespace_only__returns_empty_list():
    """Purpose: Comma/whitespace-only input produces no chunks.

    Why this matters: Avoids sending invalid or empty request params to the API.
    Setup summary: Call _chunk_message_ids("  ,  ,  "). Assert result is [].
    """
    assert _chunk_message_ids("  ,  ,  ") == []


@pytest.mark.ai
def test_chunk_message_ids__single_id__returns_one_chunk():
    """Purpose: Single message ID yields one chunk.

    Why this matters: Common case; must not be split.
    Setup summary: Call _chunk_message_ids("msg-1"). Assert result is ["msg-1"].
    """
    assert _chunk_message_ids("msg-1") == ["msg-1"]


@pytest.mark.ai
def test_chunk_message_ids__leading_trailing_whitespace__stripped():
    """Purpose: Whitespace around IDs and commas is stripped.

    Why this matters: API expects comma-separated IDs without extra spaces; parsing must normalize.
    Setup summary: Call _chunk_message_ids(" msg-1 , msg-2 "). Assert one chunk with "msg-1,msg-2".
    """
    assert _chunk_message_ids(" msg-1 , msg-2 ") == ["msg-1,msg-2"]


@pytest.mark.ai
def test_chunk_message_ids__exactly_page_size__returns_one_chunk():
    """Purpose: Exactly MESSAGE_IDS_PAGE_SIZE IDs fit in one chunk.

    Why this matters: Boundary ensures we do not over-paginate at the limit.
    Setup summary: Build 200 IDs, chunk. Assert len(chunks) == 1 and chunk has 199 commas.
    """
    ids = [f"m{i}" for i in range(MESSAGE_IDS_PAGE_SIZE)]
    chunks = _chunk_message_ids(",".join(ids))
    assert len(chunks) == 1
    assert chunks[0].count(",") == MESSAGE_IDS_PAGE_SIZE - 1


@pytest.mark.ai
def test_chunk_message_ids__over_page_size__returns_two_chunks():
    """Purpose: One more than page size triggers two chunks.

    Why this matters: Pagination must kick in so API limit is never exceeded.
    Setup summary: Build 201 IDs, chunk. Assert two chunks; second has single ID.
    """
    ids = [f"m{i}" for i in range(MESSAGE_IDS_PAGE_SIZE + 1)]
    chunks = _chunk_message_ids(",".join(ids))
    assert len(chunks) == 2
    assert chunks[0].count(",") == MESSAGE_IDS_PAGE_SIZE - 1
    assert chunks[1] == f"m{MESSAGE_IDS_PAGE_SIZE}"


@pytest.mark.ai
def test_chunk_message_ids__two_full_pages__returns_two_chunks():
    """Purpose: Two full pages of IDs produce two equal-sized chunks.

    Why this matters: Ensures correct chunk sizing for large message ID lists.
    Setup summary: Build 400 IDs, chunk. Assert two chunks, each with 199 commas.
    """
    ids = [f"m{i}" for i in range(MESSAGE_IDS_PAGE_SIZE * 2)]
    chunks = _chunk_message_ids(",".join(ids))
    assert len(chunks) == 2
    assert all(c.count(",") == MESSAGE_IDS_PAGE_SIZE - 1 for c in chunks)


# --- ToolCall class methods (mocked) ---


@pytest.mark.ai
def test_create_many__success__returns_list_object(mocker):
    """Purpose: create_many calls POST /messages/tools and returns a ListObject.

    Why this matters: Toolkit/orchestrator rely on this for persisting tool calls.
    Setup summary: Mock _static_request to return a ListObject. Call create_many. Assert type and params.
    """
    mocker.patch.object(
        ToolCall, "_static_request", return_value=_make_list_object([{"id": "tc-1"}])
    )
    result = ToolCall.create_many("user", "company", messageId="msg-1", tools=[])
    assert isinstance(result, ListObject)
    assert result.get("data") == [{"id": "tc-1"}]
    ToolCall._static_request.assert_called_once_with(
        "post",
        "/messages/tools",
        "user",
        "company",
        params={"messageId": "msg-1", "tools": []},
    )


@pytest.mark.ai
def test_list__success__returns_list_object(mocker):
    """Purpose: list calls GET /messages/tools with messageIds and returns ListObject.

    Why this matters: Callers need to load tool calls by message IDs.
    Setup summary: Mock _static_request. Call list with messageIds. Assert call args and return type.
    """
    mocker.patch.object(ToolCall, "_static_request", return_value=_make_list_object([]))
    result = ToolCall.list("user", "company", messageIds="msg-1,msg-2")
    assert isinstance(result, ListObject)
    ToolCall._static_request.assert_called_once_with(
        "get",
        "/messages/tools",
        "user",
        "company",
        params={"messageIds": "msg-1,msg-2"},
    )


@pytest.mark.ai
def test_list_by_message_ids__empty_message_ids__returns_empty_without_request(mocker):
    """Purpose: Empty messageIds returns empty list without calling the API.

    Why this matters: Avoids unnecessary HTTP when there are no messages to query.
    Setup summary: Patch _static_request. Call list_by_message_ids with messageIds="". Assert data==[] and _static_request not called.
    """
    mocker.patch.object(ToolCall, "_static_request")
    result = ToolCall.list_by_message_ids("user", "company", messageIds="")
    assert isinstance(result, ListObject)
    assert result.get("data") == []
    ToolCall._static_request.assert_not_called()


@pytest.mark.ai
def test_list_by_message_ids__single_chunk__calls_api_once(mocker):
    """Purpose: Fewer than 201 IDs result in a single GET.

    Why this matters: No pagination when under the API limit.
    Setup summary: Mock _static_request. Call list_by_message_ids with one ID. Assert one call and data.
    """
    mocker.patch.object(
        ToolCall, "_static_request", return_value=_make_list_object([{"id": "tc-1"}])
    )
    result = ToolCall.list_by_message_ids("user", "company", messageIds="msg-1")
    assert len(result.get("data", [])) == 1
    ToolCall._static_request.assert_called_once_with(
        "get", "/messages/tools", "user", "company", params={"messageIds": "msg-1"}
    )


@pytest.mark.ai
def test_list_by_message_ids__multiple_chunks__merges_data(mocker):
    """Purpose: Over 200 IDs trigger multiple GETs and merged data.

    Why this matters: Long chats must not hit the 200-messageIds limit; results must be combined.
    Setup summary: 210 IDs. side_effect returns two ListObjects. Assert merged data and call_count==2.
    """
    ids = [f"m{i}" for i in range(MESSAGE_IDS_PAGE_SIZE + 10)]
    msg_ids_str = ",".join(ids)
    mocker.patch.object(
        ToolCall,
        "_static_request",
        side_effect=[
            _make_list_object([{"id": "page1"}]),
            _make_list_object([{"id": "page2"}]),
        ],
    )
    result = ToolCall.list_by_message_ids("user", "company", messageIds=msg_ids_str)
    assert result.get("data") == [{"id": "page1"}, {"id": "page2"}]
    assert ToolCall._static_request.call_count == 2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_many_async__success__returns_list_object(mocker):
    """Purpose: create_many_async returns ListObject like sync create_many.

    Why this matters: Async callers (e.g. orchestrator) need the same contract.
    Setup summary: Mock _static_request_async. Await create_many_async. Assert ListObject and one call.
    """
    mocker.patch.object(
        ToolCall, "_static_request_async", return_value=_make_list_object([])
    )
    result = await ToolCall.create_many_async(
        "user", "company", messageId="msg-1", tools=[]
    )
    assert isinstance(result, ListObject)
    ToolCall._static_request_async.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_list_by_message_ids_async__empty_message_ids__returns_empty_without_request(
    mocker,
):
    """Purpose: Async list_by_message_ids with empty messageIds does not call API.

    Why this matters: Same early-exit behavior as sync for consistency.
    Setup summary: Patch _static_request_async. Await list_by_message_ids_async with messageIds="". Assert empty data, no call.
    """
    mocker.patch.object(ToolCall, "_static_request_async")
    result = await ToolCall.list_by_message_ids_async("user", "company", messageIds="")
    assert isinstance(result, ListObject)
    assert result.get("data") == []
    ToolCall._static_request_async.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_list_by_message_ids_async__multiple_chunks__merges_data(mocker):
    """Purpose: Async list_by_message_ids paginates and merges like sync.

    Why this matters: Long async loads must also respect the 200-ID limit and merge pages.
    Setup summary: 210 IDs, side_effect two ListObjects. Await list_by_message_ids_async. Assert merged data, call_count 2.
    """
    ids = [f"m{i}" for i in range(MESSAGE_IDS_PAGE_SIZE + 10)]
    msg_ids_str = ",".join(ids)
    mocker.patch.object(
        ToolCall,
        "_static_request_async",
        side_effect=[
            _make_list_object([{"id": "a"}]),
            _make_list_object([{"id": "b"}]),
        ],
    )
    result = await ToolCall.list_by_message_ids_async(
        "user", "company", messageIds=msg_ids_str
    )
    assert result.get("data") == [{"id": "a"}, {"id": "b"}]
    assert ToolCall._static_request_async.call_count == 2
