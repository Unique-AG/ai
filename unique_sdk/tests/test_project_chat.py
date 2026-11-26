from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

import unique_sdk
from unique_sdk._util import convert_to_unique_object
from unique_sdk.api_resources._project_chat import ProjectChat, ProjectChatChunk

pytestmark = pytest.mark.ai

USER_ID = "user_1"
COMPANY_ID = "company_1"
PROJECT_ID = "custom_space_1"
CHAT_ID = "chat_1"
SEARCH_URL = "/search/project-chats"
CHUNKS_URL = "/search/project-chats/chunks"
RECENT_URL = "/search/project-chats/recent"

CHUNK = {
    "chatId": CHAT_ID,
    "chatTitle": "Q3 budget",
    "chunkIndex": 0,
    "pairIndexStart": 1,
    "pairIndexEnd": 3,
    "messageIds": ["msg_1", "msg_2"],
    "text": "User: What is the Q3 budget?\nAssistant: 1.2M CHF.",
    "tokenCount": 18,
    "isOpen": False,
    "createdAt": "2026-11-19T12:00:00.000Z",
    "updatedAt": "2026-11-19T12:05:00.000Z",
    "score": 0.82,
    "highlights": ["the <em>Q3 budget</em>"],
    "object": "search.project-chat-chunk",
}
CHUNK_LIST = {
    "object": "list",
    "data": [CHUNK],
    "chatStats": [],
    "nextCursor": None,
}
CHAT = {
    "chatId": CHAT_ID,
    "chatTitle": "Q3 budget",
    "chatCreatedAt": "2026-11-19T12:00:00.000Z",
    "updatedAt": "2026-11-20T09:00:00.000Z",
    "chunkCount": 4,
    "object": "search.project-chat",
}
CHAT_LIST = {"object": "list", "data": [CHAT], "nextCursor": "cursor_2"}


def test_project_chat_resources_are_exported():
    assert unique_sdk.ProjectChat is ProjectChat
    assert unique_sdk.ProjectChatChunk is ProjectChatChunk
    assert ProjectChat.OBJECT_NAME == "search.project-chat"
    assert ProjectChatChunk.OBJECT_NAME == "search.project-chat-chunk"


def test_chunk_list_items_convert_to_project_chat_chunks():
    result = convert_to_unique_object(dict(CHUNK_LIST), USER_ID, COMPANY_ID)

    assert isinstance(result, unique_sdk.ListObject)
    assert isinstance(result.data[0], ProjectChatChunk)
    assert result.data[0].highlights == ["the <em>Q3 budget</em>"]
    assert result["nextCursor"] is None


def test_chat_list_items_convert_to_project_chats():
    result = convert_to_unique_object(dict(CHAT_LIST), USER_ID, COMPANY_ID)

    assert isinstance(result.data[0], ProjectChat)
    assert result.data[0].chunkCount == 4
    assert result["nextCursor"] == "cursor_2"


@patch.object(ProjectChat, "_static_request")
def test_search_sends_only_the_query_and_project(mock_request):
    # Unset filters are left out so the endpoint applies its own defaults.
    mock_request.return_value = CHUNK_LIST

    result = ProjectChat.search(
        USER_ID, COMPANY_ID, project_id=PROJECT_ID, query="Q3 budget"
    )

    mock_request.assert_called_once_with(
        "post",
        SEARCH_URL,
        USER_ID,
        COMPANY_ID,
        params={"projectId": PROJECT_ID, "query": "Q3 budget"},
    )
    assert result == CHUNK_LIST


@patch.object(ProjectChat, "_static_request")
def test_search_sends_all_filters_in_camel_case(mock_request):
    mock_request.return_value = CHUNK_LIST
    after = datetime(2026, 11, 1, tzinfo=timezone.utc)

    ProjectChat.search(
        USER_ID,
        COMPANY_ID,
        project_id=PROJECT_ID,
        query="Q3 budget",
        chat_ids=["chat_2"],
        exclude_chat_ids=["chat_current"],
        created_after=after,
        created_before="2026-11-20T00:00:00Z",
        limit=5,
        include_chat_stats=True,
    )

    mock_request.assert_called_once_with(
        "post",
        SEARCH_URL,
        USER_ID,
        COMPANY_ID,
        params={
            "projectId": PROJECT_ID,
            "query": "Q3 budget",
            "chatIds": ["chat_2"],
            "excludeChatIds": ["chat_current"],
            "createdAfter": "2026-11-01T00:00:00+00:00",
            "createdBefore": "2026-11-20T00:00:00Z",
            "limit": 5,
            "includeChatStats": True,
        },
    )


@patch.object(ProjectChat, "_static_request")
def test_search_keeps_false_and_empty_values(mock_request):
    # Only None means "not set"; False and [] are real values.
    mock_request.return_value = CHUNK_LIST

    ProjectChat.search(
        USER_ID,
        COMPANY_ID,
        project_id=PROJECT_ID,
        query="q",
        exclude_chat_ids=[],
        include_chat_stats=False,
    )

    assert mock_request.call_args.kwargs["params"] == {
        "projectId": PROJECT_ID,
        "query": "q",
        "excludeChatIds": [],
        "includeChatStats": False,
    }


@patch.object(ProjectChat, "_static_request")
def test_list_chunks_pages_through_one_chat(mock_request):
    mock_request.return_value = CHUNK_LIST

    result = ProjectChat.list_chunks(
        USER_ID,
        COMPANY_ID,
        project_id=PROJECT_ID,
        chat_id=CHAT_ID,
        limit=10,
        after="cursor_1",
        include_chat_stats=True,
    )

    mock_request.assert_called_once_with(
        "post",
        CHUNKS_URL,
        USER_ID,
        COMPANY_ID,
        params={
            "projectId": PROJECT_ID,
            "chatId": CHAT_ID,
            "limit": 10,
            "after": "cursor_1",
            "includeChatStats": True,
        },
    )
    assert result == CHUNK_LIST


@patch.object(ProjectChat, "_static_request")
def test_list_recent_sends_filters_and_cursor(mock_request):
    mock_request.return_value = CHAT_LIST
    before = datetime(2026, 11, 20, 8, 30, tzinfo=timezone.utc)

    result = ProjectChat.list_recent(
        USER_ID,
        COMPANY_ID,
        project_id=PROJECT_ID,
        exclude_chat_ids=["chat_current"],
        updated_after="2026-11-01T00:00:00Z",
        updated_before=before,
        limit=20,
        after="cursor_1",
    )

    mock_request.assert_called_once_with(
        "post",
        RECENT_URL,
        USER_ID,
        COMPANY_ID,
        params={
            "projectId": PROJECT_ID,
            "excludeChatIds": ["chat_current"],
            "updatedAfter": "2026-11-01T00:00:00Z",
            "updatedBefore": "2026-11-20T08:30:00+00:00",
            "limit": 20,
            "after": "cursor_1",
        },
    )
    assert result == CHAT_LIST


@patch.object(ProjectChat, "_static_request")
def test_list_recent_sends_only_the_project(mock_request):
    mock_request.return_value = CHAT_LIST

    ProjectChat.list_recent(USER_ID, COMPANY_ID, project_id=PROJECT_ID)

    mock_request.assert_called_once_with(
        "post", RECENT_URL, USER_ID, COMPANY_ID, params={"projectId": PROJECT_ID}
    )


@patch.object(ProjectChat, "_static_request_async", new_callable=AsyncMock)
async def test_search_async_posts_the_query(mock_request):
    mock_request.return_value = CHUNK_LIST

    result = await ProjectChat.search_async(
        USER_ID,
        COMPANY_ID,
        project_id=PROJECT_ID,
        query="Q3 budget",
        exclude_chat_ids=["chat_current"],
    )

    mock_request.assert_awaited_once_with(
        "post",
        SEARCH_URL,
        USER_ID,
        COMPANY_ID,
        params={
            "projectId": PROJECT_ID,
            "query": "Q3 budget",
            "excludeChatIds": ["chat_current"],
        },
    )
    assert result == CHUNK_LIST


@patch.object(ProjectChat, "_static_request_async", new_callable=AsyncMock)
async def test_list_chunks_async_reads_one_chat(mock_request):
    mock_request.return_value = CHUNK_LIST

    result = await ProjectChat.list_chunks_async(
        USER_ID, COMPANY_ID, project_id=PROJECT_ID, chat_id=CHAT_ID
    )

    mock_request.assert_awaited_once_with(
        "post",
        CHUNKS_URL,
        USER_ID,
        COMPANY_ID,
        params={"projectId": PROJECT_ID, "chatId": CHAT_ID},
    )
    assert result == CHUNK_LIST


@patch.object(ProjectChat, "_static_request_async", new_callable=AsyncMock)
async def test_list_recent_async_lists_chats(mock_request):
    mock_request.return_value = CHAT_LIST

    result = await ProjectChat.list_recent_async(
        USER_ID, COMPANY_ID, project_id=PROJECT_ID, limit=5
    )

    mock_request.assert_awaited_once_with(
        "post",
        RECENT_URL,
        USER_ID,
        COMPANY_ID,
        params={"projectId": PROJECT_ID, "limit": 5},
    )
    assert result == CHAT_LIST


@pytest.mark.parametrize(
    "option",
    [{"api_key": "ukey_x"}, {"api_base": "https://x"}, {"headers": {"x": "y"}}],
)
@patch.object(ProjectChat, "_static_request")
def test_request_options_are_rejected_instead_of_sent(mock_request, option):
    with pytest.raises(TypeError):
        ProjectChat.search(  # type: ignore[call-arg]
            USER_ID, COMPANY_ID, project_id=PROJECT_ID, query="q", **option
        )
    with pytest.raises(TypeError):
        ProjectChat.list_chunks(  # type: ignore[call-arg]
            USER_ID, COMPANY_ID, project_id=PROJECT_ID, chat_id=CHAT_ID, **option
        )
    with pytest.raises(TypeError):
        ProjectChat.list_recent(  # type: ignore[call-arg]
            USER_ID, COMPANY_ID, project_id=PROJECT_ID, **option
        )
    mock_request.assert_not_called()


@patch.object(ProjectChat, "_static_request")
def test_project_id_must_be_passed_by_keyword(mock_request):
    with pytest.raises(TypeError):
        ProjectChat.search(USER_ID, COMPANY_ID, PROJECT_ID, "q")  # type: ignore[misc]
    mock_request.assert_not_called()
