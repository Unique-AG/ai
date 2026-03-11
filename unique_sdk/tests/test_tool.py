"""Tests for Tool API resource and helpers.

Conforms to unique_skills/.claude/skills/python-testing (naming, docstrings, mocker, ai mark).
"""

import pytest

from unique_sdk import Tool as ToolPublic
from unique_sdk._list_object import ListObject
from unique_sdk.api_resources._tool import (
    _MESSAGE_IDS_PAGE_SIZE,
    Tool,
    _chunk_message_ids,
)


@pytest.mark.ai
def test_tool_exported_from_unique_sdk():
    """Purpose: Tool is importable from unique_sdk (public API).

    Why this matters: Ensures the new export in unique_sdk/__init__.py is covered
    so diff-coverage on changed lines passes in CI.
    Setup summary: Import Tool from unique_sdk. Assert it is the same class as the module-level Tool.
    """
    assert ToolPublic is Tool


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

    Why this matters: Callers must get [] when there are no message IDs so list
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
    """Purpose: Exactly _MESSAGE_IDS_PAGE_SIZE IDs fit in one chunk.

    Why this matters: Boundary ensures we do not over-paginate at the limit.
    Setup summary: Build 200 IDs, chunk. Assert len(chunks) == 1 and chunk has 199 commas.
    """
    ids = [f"m{i}" for i in range(_MESSAGE_IDS_PAGE_SIZE)]
    chunks = _chunk_message_ids(",".join(ids))
    assert len(chunks) == 1
    assert chunks[0].count(",") == _MESSAGE_IDS_PAGE_SIZE - 1


@pytest.mark.ai
def test_chunk_message_ids__over_page_size__returns_two_chunks():
    """Purpose: One more than page size triggers two chunks.

    Why this matters: Pagination must kick in so API limit is never exceeded.
    Setup summary: Build 201 IDs, chunk. Assert two chunks; second has single ID.
    """
    ids = [f"m{i}" for i in range(_MESSAGE_IDS_PAGE_SIZE + 1)]
    chunks = _chunk_message_ids(",".join(ids))
    assert len(chunks) == 2
    assert chunks[0].count(",") == _MESSAGE_IDS_PAGE_SIZE - 1
    assert chunks[1] == f"m{_MESSAGE_IDS_PAGE_SIZE}"


@pytest.mark.ai
def test_chunk_message_ids__two_full_pages__returns_two_chunks():
    """Purpose: Two full pages of IDs produce two equal-sized chunks.

    Why this matters: Ensures correct chunk sizing for large message ID lists.
    Setup summary: Build 400 IDs, chunk. Assert two chunks, each with 199 commas.
    """
    ids = [f"m{i}" for i in range(_MESSAGE_IDS_PAGE_SIZE * 2)]
    chunks = _chunk_message_ids(",".join(ids))
    assert len(chunks) == 2
    assert all(c.count(",") == _MESSAGE_IDS_PAGE_SIZE - 1 for c in chunks)


# --- Tool class methods (mocked) ---


@pytest.mark.ai
def test_create_many__success__returns_list_object(mocker):
    """Purpose: create_many calls POST /messages/tools and returns a ListObject.

    Why this matters: Toolkit/orchestrator rely on this for persisting tool calls.
    Setup summary: Mock _static_request to return a ListObject. Call create_many. Assert type and params.
    """
    mocker.patch.object(
        Tool, "_static_request", return_value=_make_list_object([{"id": "tc-1"}])
    )
    result = Tool.create_many("user", "company", messageId="msg-1", tools=[])
    assert isinstance(result, ListObject)
    assert result.get("data") == [{"id": "tc-1"}]
    Tool._static_request.assert_called_once_with(
        "post",
        "/messages/tools",
        "user",
        "company",
        params={"messageId": "msg-1", "tools": []},
    )


@pytest.mark.ai
def test_create_many__non_list_object_response__raises_type_error(mocker):
    """Purpose: create_many raises TypeError when API returns something other than ListObject.

    Why this matters: Defensive check so callers get a clear error.
    Setup summary: Mock _static_request to return a dict. Call create_many. Expect TypeError.
    """
    mocker.patch.object(Tool, "_static_request", return_value={"data": []})
    with pytest.raises(TypeError, match="Expected list object from API"):
        Tool.create_many("user", "company", messageId="msg-1", tools=[])


@pytest.mark.ai
def test_list__empty_message_ids__returns_empty_without_request(mocker):
    """Purpose: Empty messageIds returns empty list without calling the API.

    Why this matters: Avoids unnecessary HTTP when there are no messages to query.
    Setup summary: Patch _static_request. Call list with messageIds="". Assert data==[] and no API call.
    """
    mocker.patch.object(Tool, "_static_request")
    result = Tool.list("user", "company", messageIds="")
    assert isinstance(result, ListObject)
    assert result.get("data") == []
    Tool._static_request.assert_not_called()


@pytest.mark.ai
def test_list__single_chunk__calls_api_once(mocker):
    """Purpose: Fewer than 201 IDs result in a single GET.

    Why this matters: No pagination when under the API limit.
    Setup summary: Mock _static_request. Call list with two IDs. Assert one call with normalized params.
    """
    mocker.patch.object(
        Tool, "_static_request", return_value=_make_list_object([{"id": "tc-1"}])
    )
    result = Tool.list("user", "company", messageIds="msg-1,msg-2")
    assert isinstance(result, ListObject)
    assert len(result.get("data", [])) == 1
    Tool._static_request.assert_called_once_with(
        "get",
        "/messages/tools",
        "user",
        "company",
        params={"messageIds": "msg-1,msg-2"},
    )


@pytest.mark.ai
def test_list__multiple_chunks__merges_data(mocker):
    """Purpose: Over 200 IDs trigger multiple GETs and merged data.

    Why this matters: Long chats must not hit the 200-messageIds limit; results must be combined.
    Setup summary: 210 IDs. side_effect returns two ListObjects. Assert merged data and call_count==2.
    """
    ids = [f"m{i}" for i in range(_MESSAGE_IDS_PAGE_SIZE + 10)]
    msg_ids_str = ",".join(ids)
    mocker.patch.object(
        Tool,
        "_static_request",
        side_effect=[
            _make_list_object([{"id": "page1"}]),
            _make_list_object([{"id": "page2"}]),
        ],
    )
    result = Tool.list("user", "company", messageIds=msg_ids_str)
    assert result.get("data") == [{"id": "page1"}, {"id": "page2"}]
    assert Tool._static_request.call_count == 2


@pytest.mark.ai
def test_list__single_chunk_non_list_object__raises_type_error(mocker):
    """Purpose: list raises TypeError when single-chunk API response is not ListObject.

    Why this matters: Callers get a clear error instead of AttributeError on .get("data").
    Setup summary: Mock _static_request to return a dict. Call with one ID. Expect TypeError.
    """
    mocker.patch.object(Tool, "_static_request", return_value={"data": []})
    with pytest.raises(TypeError, match="Expected list object from API"):
        Tool.list("user", "company", messageIds="msg-1")


@pytest.mark.ai
def test_list__multi_chunk_page_not_list_object__raises_type_error(
    mocker,
):
    """Purpose: list raises TypeError when a paginated page is not ListObject.

    Why this matters: Defensive check when merging multiple pages.
    Setup summary: 210 IDs; first call returns ListObject, second returns dict. Expect TypeError.
    """
    ids = [f"m{i}" for i in range(_MESSAGE_IDS_PAGE_SIZE + 10)]
    mocker.patch.object(
        Tool,
        "_static_request",
        side_effect=[
            _make_list_object([{"id": "a"}]),
            {"data": []},
        ],
    )
    with pytest.raises(TypeError, match="Expected list object from API"):
        Tool.list("user", "company", messageIds=",".join(ids))


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_many_async__success__returns_list_object(mocker):
    """Purpose: create_many_async returns ListObject like sync create_many.

    Why this matters: Async callers (e.g. orchestrator) need the same contract.
    Setup summary: Mock _static_request_async. Await create_many_async. Assert ListObject and one call.
    """
    mocker.patch.object(
        Tool, "_static_request_async", return_value=_make_list_object([])
    )
    result = await Tool.create_many_async(
        "user", "company", messageId="msg-1", tools=[]
    )
    assert isinstance(result, ListObject)
    Tool._static_request_async.assert_called_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_many_async__non_list_object_response__raises_type_error(mocker):
    """Purpose: create_many_async raises TypeError when API returns non-ListObject.

    Why this matters: Same defensive contract as sync create_many.
    Setup summary: Mock _static_request_async to return dict. Await create_many_async. Expect TypeError.
    """
    mocker.patch.object(Tool, "_static_request_async", return_value={"data": []})
    with pytest.raises(TypeError, match="Expected list object from API"):
        await Tool.create_many_async("user", "company", messageId="msg-1", tools=[])


@pytest.mark.ai
@pytest.mark.asyncio
async def test_list_async__empty_message_ids__returns_empty_without_request(mocker):
    """Purpose: Async list with empty messageIds does not call API.

    Why this matters: Same early-exit behavior as sync for consistency.
    Setup summary: Patch _static_request_async. Await list_async with messageIds="". Assert empty data, no call.
    """
    mocker.patch.object(Tool, "_static_request_async")
    result = await Tool.list_async("user", "company", messageIds="")
    assert isinstance(result, ListObject)
    assert result.get("data") == []
    Tool._static_request_async.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_list_async__single_chunk__calls_api_once(mocker):
    """Purpose: list_async with IDs under the limit calls API once and returns ListObject.

    Why this matters: Single-chunk path must be covered for async as well as sync.
    Setup summary: Mock _static_request_async. Await list_async with two IDs. Assert one call.
    """
    mocker.patch.object(
        Tool,
        "_static_request_async",
        return_value=_make_list_object([{"id": "tc-1"}]),
    )
    result = await Tool.list_async("user", "company", messageIds="msg-1,msg-2")
    assert isinstance(result, ListObject)
    assert len(result.get("data", [])) == 1
    Tool._static_request_async.assert_called_once_with(
        "get",
        "/messages/tools",
        "user",
        "company",
        params={"messageIds": "msg-1,msg-2"},
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_list_async__single_chunk_non_list_object__raises_type_error(mocker):
    """Purpose: list_async raises TypeError when single-chunk response is not ListObject.

    Why this matters: Same defensive contract as sync single-chunk path.
    Setup summary: Mock _static_request_async to return dict. Await with one ID. Expect TypeError.
    """
    mocker.patch.object(Tool, "_static_request_async", return_value={"data": []})
    with pytest.raises(TypeError, match="Expected list object from API"):
        await Tool.list_async("user", "company", messageIds="msg-1")


@pytest.mark.ai
@pytest.mark.asyncio
async def test_list_async__multiple_chunks__merges_data(mocker):
    """Purpose: Async list paginates and merges like sync.

    Why this matters: Long async loads must also respect the 200-ID limit and merge pages.
    Setup summary: 210 IDs, side_effect two ListObjects. Await list_async. Assert merged data, call_count 2.
    """
    ids = [f"m{i}" for i in range(_MESSAGE_IDS_PAGE_SIZE + 10)]
    msg_ids_str = ",".join(ids)
    mocker.patch.object(
        Tool,
        "_static_request_async",
        side_effect=[
            _make_list_object([{"id": "a"}]),
            _make_list_object([{"id": "b"}]),
        ],
    )
    result = await Tool.list_async("user", "company", messageIds=msg_ids_str)
    assert result.get("data") == [{"id": "a"}, {"id": "b"}]
    assert Tool._static_request_async.call_count == 2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_list_async__multi_chunk_page_not_list_object__raises_type_error(
    mocker,
):
    """Purpose: list_async raises TypeError when a paginated page is not ListObject.

    Why this matters: Defensive check when merging multiple async pages.
    Setup summary: 210 IDs; first async call returns ListObject, second returns dict. Expect TypeError.
    """
    ids = [f"m{i}" for i in range(_MESSAGE_IDS_PAGE_SIZE + 10)]
    mocker.patch.object(
        Tool,
        "_static_request_async",
        side_effect=[
            _make_list_object([{"id": "a"}]),
            {"data": []},
        ],
    )
    with pytest.raises(TypeError, match="Expected list object from API"):
        await Tool.list_async("user", "company", messageIds=",".join(ids))
