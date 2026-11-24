"""Unit tests for :mod:`unique_toolkit.experimental.resources.project_chat`.

The SDK is patched at the ``unique_sdk.ProjectChat`` boundary, so drift in
method names or keyword arguments between toolkit and SDK shows up here. The
sample responses are the shapes the QA endpoints returned.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.experimental.resources.project_chat import (
    ProjectChatChunkPage,
    ProjectChats,
    ProjectChatSummaryPage,
)

USER_ID = "user_1"
COMPANY_ID = "company_1"
PROJECT_ID = "custom_space_1"
CHAT_ID = "chat_fceuqhfih8htb9gj8euabl6j"

CHUNK_LIST: dict = {
    "object": "list",
    "data": [
        {
            "object": "search.project-chat-chunk",
            "chatId": CHAT_ID,
            "chatTitle": "Current CEO of NVIDIA",
            "chunkIndex": 0,
            "pairIndexStart": 1,
            "pairIndexEnd": 1,
            "messageIds": [
                "msg_k20i0d7veiav8te7l43oiacr",
                "msg_q1z1q4r53vzrpq82h9ziumv8",
            ],
            "text": "[pair 1 · 2026-11-24T14:17:09Z]\nUser: who is now the CEO of NVIDIA?\nAssistant: Jensen Huang.",
            "tokenCount": 95,
            "isOpen": True,
            "createdAt": "2026-11-24T14:17:09.286Z",
            "updatedAt": "2026-11-24T14:17:34.336Z",
            "score": 28.67546,
            "highlights": ["who is now the <em>CEO</em> of NVIDIA?"],
        }
    ],
    "chatStats": [{"chatId": CHAT_ID, "chunkCount": 1, "tokenCount": 95}],
    "nextCursor": None,
}

CHAT_LIST: dict = {
    "object": "list",
    "data": [
        {
            "object": "search.project-chat",
            "chatId": "chat_ki71hutksan6nc1pxdcy36it",
            "chatTitle": "Accessing Unique platform QA",
            "chatCreatedAt": "2026-11-24T14:17:53.050Z",
            "updatedAt": "2026-11-24T14:18:40.196Z",
            "chunkCount": 1,
        }
    ],
    "nextCursor": "WzE3OTU1Mjk4NTQzMzYsImNoYXRfZmNldXFoZmloOGh0YjlnajhldWFibDZqIl0",
}


@pytest.fixture
def service() -> ProjectChats:
    return ProjectChats(user_id=USER_ID, company_id=COMPANY_ID, project_id=PROJECT_ID)


def _chat_event(payload_extra: dict) -> ChatEvent:
    return ChatEvent.model_validate(
        {
            "id": "event1",
            "event": "unique.chat.external-module.chosen",
            "userId": USER_ID,
            "companyId": COMPANY_ID,
            "payload": {
                "name": "test_module",
                "description": "Test description",
                "configuration": {},
                "chatId": "chat_current",
                "assistantId": "assistant1",
                "userMessage": {
                    "id": "msg1",
                    "text": "Hello",
                    "createdAt": "2023-01-01T00:00:00Z",
                    "originalText": "Hello",
                    "language": "en",
                },
                "assistantMessage": {"id": "msg2", "createdAt": "2023-01-01T00:01:00Z"},
                **payload_extra,
            },
        }
    )


# ── Event field ───────────────────────────────────────────────────────────────


@pytest.mark.ai
def test_chat_event_reads_project_id_from_the_wire() -> None:
    assert _chat_event({"projectId": PROJECT_ID}).payload.project_id == PROJECT_ID


@pytest.mark.ai
def test_chat_event_without_project_id_defaults_to_none() -> None:
    assert _chat_event({}).payload.project_id is None


# ── Construction ──────────────────────────────────────────────────────────────


@pytest.mark.ai
def test_from_event_binds_the_event_user_company_and_project() -> None:
    service = ProjectChats.from_event(_chat_event({"projectId": PROJECT_ID}))

    assert service.project_id == PROJECT_ID
    assert service._user_id == USER_ID
    assert service._company_id == COMPANY_ID


@pytest.mark.ai
def test_from_event_raises_for_a_chat_outside_a_project() -> None:
    with pytest.raises(ValueError, match="project_id"):
        ProjectChats.from_event(_chat_event({}))


@pytest.mark.ai
def test_constructor_rejects_an_empty_project_id() -> None:
    with pytest.raises(ValueError):
        ProjectChats(user_id=USER_ID, company_id=COMPANY_ID, project_id="")


# ── Mapping ───────────────────────────────────────────────────────────────────


@pytest.mark.ai
def test_search_maps_the_chunk_list(
    monkeypatch: pytest.MonkeyPatch, service: ProjectChats
) -> None:
    sdk = MagicMock(return_value=CHUNK_LIST)
    monkeypatch.setattr("unique_sdk.ProjectChat.search", sdk)

    page = service.search(query="CEO", exclude_chat_ids=["chat_current"], limit=5)

    assert isinstance(page, ProjectChatChunkPage)
    chunk = page.chunks[0]
    assert chunk.chat_id == CHAT_ID
    assert chunk.chat_title == "Current CEO of NVIDIA"
    assert (chunk.pair_index_start, chunk.pair_index_end) == (1, 1)
    assert chunk.is_open is True
    assert chunk.created_at == datetime(
        2026, 11, 24, 14, 17, 9, 286000, tzinfo=timezone.utc
    )
    assert chunk.score == pytest.approx(28.67546)
    assert page.chat_stats[0].chunk_count == 1
    assert page.next_cursor is None


@pytest.mark.ai
def test_list_recent_maps_the_chat_list(
    monkeypatch: pytest.MonkeyPatch, service: ProjectChats
) -> None:
    monkeypatch.setattr(
        "unique_sdk.ProjectChat.list_recent", MagicMock(return_value=CHAT_LIST)
    )

    page = service.list_recent()

    assert isinstance(page, ProjectChatSummaryPage)
    assert page.chats[0].chat_title == "Accessing Unique platform QA"
    assert page.chats[0].chat_created_at.year == 2026
    assert page.chats[0].chunk_count == 1
    assert page.next_cursor == CHAT_LIST["nextCursor"]


@pytest.mark.ai
def test_chunks_without_title_score_or_highlights_parse(
    monkeypatch: pytest.MonkeyPatch, service: ProjectChats
) -> None:
    chunk = {
        **CHUNK_LIST["data"][0],
        "chatTitle": None,
        "score": None,
        "highlights": None,
    }
    payload = {**CHUNK_LIST, "data": [chunk], "chatStats": []}
    monkeypatch.setattr(
        "unique_sdk.ProjectChat.list_chunks", MagicMock(return_value=payload)
    )

    page = service.list_chunks(chat_id=CHAT_ID)

    assert page.chunks[0].chat_title is None
    assert page.chunks[0].score is None
    assert page.chunks[0].highlights is None
    assert page.chat_stats == []


# ── SDK calls (sync) ──────────────────────────────────────────────────────────


@pytest.mark.ai
def test_search_passes_every_argument_to_the_sdk(
    monkeypatch: pytest.MonkeyPatch, service: ProjectChats
) -> None:
    sdk = MagicMock(return_value=CHUNK_LIST)
    monkeypatch.setattr("unique_sdk.ProjectChat.search", sdk)
    after = datetime(2026, 11, 1, tzinfo=timezone.utc)
    before = datetime(2026, 11, 30, tzinfo=timezone.utc)

    service.search(
        query="CEO",
        chat_ids=["chat_a"],
        exclude_chat_ids=["chat_current"],
        created_after=after,
        created_before=before,
        limit=5,
        include_chat_stats=True,
    )

    sdk.assert_called_once_with(
        USER_ID,
        COMPANY_ID,
        project_id=PROJECT_ID,
        query="CEO",
        chat_ids=["chat_a"],
        exclude_chat_ids=["chat_current"],
        created_after=after,
        created_before=before,
        limit=5,
        include_chat_stats=True,
    )


@pytest.mark.ai
def test_list_chunks_passes_the_chat_and_cursor(
    monkeypatch: pytest.MonkeyPatch, service: ProjectChats
) -> None:
    sdk = MagicMock(return_value=CHUNK_LIST)
    monkeypatch.setattr("unique_sdk.ProjectChat.list_chunks", sdk)

    service.list_chunks(
        chat_id=CHAT_ID, limit=10, after="cursor_1", include_chat_stats=True
    )

    sdk.assert_called_once_with(
        USER_ID,
        COMPANY_ID,
        project_id=PROJECT_ID,
        chat_id=CHAT_ID,
        limit=10,
        after="cursor_1",
        include_chat_stats=True,
    )


@pytest.mark.ai
def test_list_recent_passes_filters_and_cursor(
    monkeypatch: pytest.MonkeyPatch, service: ProjectChats
) -> None:
    sdk = MagicMock(return_value=CHAT_LIST)
    monkeypatch.setattr("unique_sdk.ProjectChat.list_recent", sdk)
    after = datetime(2026, 11, 1, tzinfo=timezone.utc)

    service.list_recent(
        exclude_chat_ids=["chat_current"],
        updated_after=after,
        limit=3,
        after="cursor_1",
    )

    sdk.assert_called_once_with(
        USER_ID,
        COMPANY_ID,
        project_id=PROJECT_ID,
        exclude_chat_ids=["chat_current"],
        updated_after=after,
        updated_before=None,
        limit=3,
        after="cursor_1",
    )


# ── SDK calls (async) ─────────────────────────────────────────────────────────


@pytest.mark.ai
@pytest.mark.asyncio
async def test_search_async_awaits_the_sdk(
    monkeypatch: pytest.MonkeyPatch, service: ProjectChats
) -> None:
    sdk = AsyncMock(return_value=CHUNK_LIST)
    monkeypatch.setattr("unique_sdk.ProjectChat.search_async", sdk)

    page = await service.search_async(query="CEO")

    assert page.chunks[0].chat_id == CHAT_ID
    assert sdk.await_args is not None
    assert sdk.await_args.kwargs["project_id"] == PROJECT_ID
    assert sdk.await_args.kwargs["query"] == "CEO"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_list_chunks_async_awaits_the_sdk(
    monkeypatch: pytest.MonkeyPatch, service: ProjectChats
) -> None:
    sdk = AsyncMock(return_value=CHUNK_LIST)
    monkeypatch.setattr("unique_sdk.ProjectChat.list_chunks_async", sdk)

    page = await service.list_chunks_async(chat_id=CHAT_ID, after="cursor_1")

    assert page.chunks[0].chunk_index == 0
    assert sdk.await_args is not None
    assert sdk.await_args.kwargs["chat_id"] == CHAT_ID
    assert sdk.await_args.kwargs["after"] == "cursor_1"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_list_recent_async_awaits_the_sdk(
    monkeypatch: pytest.MonkeyPatch, service: ProjectChats
) -> None:
    sdk = AsyncMock(return_value=CHAT_LIST)
    monkeypatch.setattr("unique_sdk.ProjectChat.list_recent_async", sdk)

    page = await service.list_recent_async(limit=1)

    assert page.chats[0].chat_id == "chat_ki71hutksan6nc1pxdcy36it"
    assert sdk.await_args is not None
    assert sdk.await_args.kwargs["limit"] == 1
