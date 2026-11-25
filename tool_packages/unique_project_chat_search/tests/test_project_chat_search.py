"""Unit tests for the ProjectChatSearch tool.

The ``ProjectChats`` resource is patched, so these tests cover the tool's own
behaviour: input normalisation, routing per mode, page walking, the sources it
returns and how its citations render.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.utils.source_handling.schema import SourceFormatConfig
from unique_toolkit.agentic.tools.utils.source_handling.source_formatting import (
    _parse_chunk,  # pyright: ignore[reportPrivateUsage]
)
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.experimental.resources.project_chat import (
    ProjectChatChunk,
    ProjectChatChunkPage,
    ProjectChats,
    ProjectChatSummary,
    ProjectChatSummaryPage,
)
from unique_toolkit.language_model.reference import add_references_to_message
from unique_toolkit.language_model.schemas import LanguageModelFunction

from unique_project_chat_search import (
    ProjectChatSearchConfig,
    ProjectChatSearchInput,
    ProjectChatSearchTool,
)
from unique_project_chat_search.schemas import parse_day

pytestmark = pytest.mark.ai

PROJECT_ID = "custom_space_1"
CURRENT_CHAT = "chat_current"
NVIDIA_CHAT = "chat_nvidia"


def _event(**payload_extra: Any) -> ChatEvent:
    return ChatEvent.model_validate(
        {
            "id": "event1",
            "event": "unique.chat.external-module.chosen",
            "userId": "user_1",
            "companyId": "company_1",
            "payload": {
                "name": "UniqueAI",
                "description": "",
                "configuration": {},
                "chatId": CURRENT_CHAT,
                "assistantId": "assistant_1",
                "userMessage": {
                    "id": "msg_1",
                    "text": "What did we say about NVIDIA?",
                    "createdAt": "2026-11-24T15:00:00Z",
                    "originalText": "What did we say about NVIDIA?",
                    "language": "en",
                },
                "assistantMessage": {
                    "id": "msg_2",
                    "createdAt": "2026-11-24T15:00:01Z",
                },
                **payload_extra,
            },
        }
    )


def _tool(event: ChatEvent | None = None, **config: Any) -> ProjectChatSearchTool:
    tool = ProjectChatSearchTool(ProjectChatSearchConfig(**config))
    tool._event = event if event is not None else _event(projectId=PROJECT_ID)  # pyright: ignore[reportPrivateUsage]
    return tool


def _call(**arguments: Any) -> LanguageModelFunction:
    return LanguageModelFunction(
        id="call_1", name="ProjectChatSearch", arguments=arguments
    )


def _chunk(
    chat_id: str = NVIDIA_CHAT,
    title: str | None = "Current CEO of NVIDIA",
    index: int = 0,
    text: str = "[pair 1 · 2026-11-24T14:17:09Z]\nUser: who is the CEO?\nAssistant: Jensen Huang.",
) -> ProjectChatChunk:
    return ProjectChatChunk(
        chat_id=chat_id,
        chat_title=title,
        chunk_index=index,
        pair_index_start=index + 1,
        pair_index_end=index + 1,
        message_ids=["msg_a", "msg_b"],
        text=text,
        token_count=20,
        is_open=True,
        created_at=datetime(2026, 11, 24, 14, 17, tzinfo=UTC),
        updated_at=datetime(2026, 11, 24, 14, 18, tzinfo=UTC),
        score=1.0,
        highlights=["<em>CEO</em>"],
    )


def _summary(
    chat_id: str = NVIDIA_CHAT, title: str | None = "Current CEO of NVIDIA"
) -> ProjectChatSummary:
    return ProjectChatSummary(
        chat_id=chat_id,
        chat_title=title,
        chat_created_at=datetime(2026, 11, 24, 14, 17, tzinfo=UTC),
        updated_at=datetime(2026, 11, 24, 14, 18, tzinfo=UTC),
        chunk_count=3,
    )


def _patch(monkeypatch: pytest.MonkeyPatch, method: str, *results: Any) -> AsyncMock:
    mock = AsyncMock(side_effect=list(results))
    monkeypatch.setattr(ProjectChats, method, mock)
    return mock


# ── Input schema ──────────────────────────────────────────────────────────────


def test_input_normalises_what_weak_models_send() -> None:
    parsed = ProjectChatSearchInput.model_validate(
        {
            "mode": " SEARCH ",
            "query": "  CEO ",
            "chat_id": "",
            "after": " ",
            "page": "2",
        }
    )

    assert parsed.mode == "search"
    assert parsed.query == "CEO"
    assert parsed.chat_id is None
    assert parsed.after is None
    assert parsed.page == 2


@pytest.mark.parametrize("page", [0, -3, None, ""])
def test_input_turns_missing_or_low_pages_into_page_one(page: Any) -> None:
    assert (
        ProjectChatSearchInput.model_validate({"mode": "recent", "page": page}).page
        == 1
    )


def test_input_ignores_unknown_fields() -> None:
    parsed = ProjectChatSearchInput.model_validate({"mode": "recent", "limit": 99})
    assert parsed.mode == "recent"


def test_parse_day_spans_the_whole_day() -> None:
    assert parse_day("2026-11-24", end_of_day=False) == datetime(
        2026, 11, 24, tzinfo=UTC
    )
    assert parse_day("2026-11-24", end_of_day=True).hour == 23
    assert parse_day("2026-11-24T10:00:00Z", end_of_day=True) == datetime(
        2026, 11, 24, 10, tzinfo=UTC
    )


def test_tool_description_uses_the_single_input_schema() -> None:
    description = _tool().tool_description()
    assert description.name == "ProjectChatSearch"
    assert description.parameters is ProjectChatSearchInput


def test_tool_is_registered_with_the_factory() -> None:
    assert ToolFactory.tool_map["ProjectChatSearch"] is ProjectChatSearchTool


# ── search ────────────────────────────────────────────────────────────────────


async def test_search_excludes_the_current_chat_and_maps_the_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search = _patch(
        monkeypatch, "search_async", ProjectChatChunkPage(chunks=[_chunk()])
    )

    response = await _tool(search_limit=5).run(
        _call(mode="search", query="CEO", after="2026-11-01", before="2026-11-24")
    )

    kwargs = search.await_args.kwargs
    assert kwargs["query"] == "CEO"
    assert kwargs["chat_ids"] is None
    assert kwargs["exclude_chat_ids"] == [CURRENT_CHAT]
    assert kwargs["created_after"] == datetime(2026, 11, 1, tzinfo=UTC)
    assert kwargs["created_before"].date().isoformat() == "2026-11-24"
    assert kwargs["limit"] == 5
    assert response.successful
    assert response.content == ""
    assert [chunk.id for chunk in response.content_chunks or []] == [NVIDIA_CHAT]


async def test_search_inside_one_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    search = _patch(monkeypatch, "search_async", ProjectChatChunkPage(chunks=[]))

    await _tool().run(_call(mode="search", query="CEO", chat_id=NVIDIA_CHAT))

    assert search.await_args.kwargs["chat_ids"] == [NVIDIA_CHAT]


async def test_search_also_excludes_the_parent_chat_of_a_sub_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search = _patch(monkeypatch, "search_async", ProjectChatChunkPage(chunks=[]))
    event = _event(
        projectId=PROJECT_ID,
        correlation={
            "parentMessageId": "msg_p",
            "parentChatId": "chat_parent",
            "parentAssistantId": "assistant_p",
        },
    )

    await _tool(event).run(_call(mode="search", query="CEO"))

    assert search.await_args.kwargs["exclude_chat_ids"] == [CURRENT_CHAT, "chat_parent"]


async def test_search_without_query_asks_for_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search = _patch(monkeypatch, "search_async")

    response = await _tool().run(_call(mode="search"))

    assert response.successful
    assert "needs a `query`" in response.content
    search.assert_not_awaited()


async def test_bad_dates_get_a_corrective_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search = _patch(monkeypatch, "search_async")

    response = await _tool().run(_call(mode="search", query="CEO", after="last week"))

    assert "2026-11-24" in response.content
    search.assert_not_awaited()


# ── read ──────────────────────────────────────────────────────────────────────


async def test_read_returns_the_chat_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    list_chunks = _patch(
        monkeypatch,
        "list_chunks_async",
        ProjectChatChunkPage(
            chunks=[_chunk(index=0), _chunk(index=1)], next_cursor=None
        ),
    )

    response = await _tool(chunks_per_page=7).run(
        _call(mode="read", chat_id=NVIDIA_CHAT)
    )

    list_chunks.assert_awaited_once_with(chat_id=NVIDIA_CHAT, limit=7, after=None)
    assert [chunk.chunk_id for chunk in response.content_chunks or []] == ["0", "1"]
    assert response.system_reminder == ""


async def test_read_page_two_continues_after_page_one_and_offers_page_three(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    list_chunks = _patch(
        monkeypatch,
        "list_chunks_async",
        ProjectChatChunkPage(chunks=[_chunk(index=0)], next_cursor="c1"),
        ProjectChatChunkPage(chunks=[_chunk(index=1)], next_cursor="c2"),
        ProjectChatChunkPage(chunks=[_chunk(index=2)], next_cursor=None),
    )

    response = await _tool(chunks_per_page=1).run(
        _call(mode="read", chat_id=NVIDIA_CHAT, page=2)
    )

    assert [call.kwargs["after"] for call in list_chunks.await_args_list] == [
        None,
        "c1",
        "c2",
    ]
    assert [chunk.chunk_id for chunk in response.content_chunks or []] == ["1"]
    assert "page=3" in response.system_reminder


async def test_read_pages_never_skip_excerpts_cut_for_the_token_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_text = "word " * 400
    chunks = [_chunk(index=i, text=long_text) for i in range(3)]

    def api_page(*_: Any, **__: Any) -> ProjectChatChunkPage:
        return ProjectChatChunkPage(chunks=chunks, next_cursor=None)

    monkeypatch.setattr(
        ProjectChats, "list_chunks_async", AsyncMock(side_effect=api_page)
    )
    tool = _tool(chunks_per_page=3, max_tokens=1200)

    first = await tool.run(_call(mode="read", chat_id=NVIDIA_CHAT))
    second = await tool.run(_call(mode="read", chat_id=NVIDIA_CHAT, page=2))

    assert [c.chunk_id for c in first.content_chunks or []] == ["0", "1"]
    assert "page=2" in first.system_reminder
    assert [c.chunk_id for c in second.content_chunks or []] == ["2"]
    assert second.system_reminder == ""


async def test_read_past_the_last_page_returns_no_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(
        monkeypatch,
        "list_chunks_async",
        ProjectChatChunkPage(chunks=[_chunk()], next_cursor=None),
    )

    response = await _tool().run(_call(mode="read", chat_id=NVIDIA_CHAT, page=2))

    assert response.content_chunks == []
    assert response.successful


async def test_read_of_an_unknown_chat_explains_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The endpoint answers an unknown chat id with an empty page, not a 404.
    _patch(monkeypatch, "list_chunks_async", ProjectChatChunkPage(chunks=[]))

    response = await _tool().run(_call(mode="read", chat_id="chat_made_up"))

    assert response.successful
    assert "No chat with that chat_id" in response.content


async def test_read_without_chat_id_asks_for_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    list_chunks = _patch(monkeypatch, "list_chunks_async")

    response = await _tool().run(_call(mode="read"))

    assert "needs a `chat_id`" in response.content
    list_chunks.assert_not_awaited()


async def test_reading_the_current_chat_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    list_chunks = _patch(monkeypatch, "list_chunks_async")

    response = await _tool().run(_call(mode="read", chat_id=CURRENT_CHAT))

    assert "already in the conversation" in response.content
    list_chunks.assert_not_awaited()


async def test_pages_beyond_max_page_are_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    list_chunks = _patch(monkeypatch, "list_chunks_async")

    response = await _tool(max_page=3).run(
        _call(mode="read", chat_id=NVIDIA_CHAT, page=4)
    )

    assert "at most 3" in response.content
    list_chunks.assert_not_awaited()


async def test_an_unknown_chat_gets_a_corrective_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NotFound(Exception):
        http_status = 404

    _patch(monkeypatch, "list_chunks_async", NotFound("Chat not found"))

    response = await _tool().run(_call(mode="read", chat_id="chat_made_up"))

    assert response.successful
    assert "No chat with that chat_id" in response.content


# ── recent ────────────────────────────────────────────────────────────────────


async def test_recent_lists_chats_as_metadata_only_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    list_recent = _patch(
        monkeypatch,
        "list_recent_async",
        ProjectChatSummaryPage(
            chats=[_summary(), _summary("chat_qa", None)], next_cursor="c1"
        ),
        ProjectChatSummaryPage(chats=[_summary("chat_old")], next_cursor=None),
    )

    response = await _tool(recent_limit=2).run(
        _call(mode="recent", query="ignored", after="2026-11-01")
    )

    kwargs = list_recent.await_args_list[0].kwargs
    assert kwargs["exclude_chat_ids"] == [CURRENT_CHAT]
    assert kwargs["updated_after"] == datetime(2026, 11, 1, tzinfo=UTC)
    assert kwargs["limit"] == 2
    chunks = response.content_chunks or []
    assert [chunk.id for chunk in chunks] == [NVIDIA_CHAT, "chat_qa"]
    assert chunks[1].title == 'Chat: "Untitled chat"'
    assert "Listing only, no content" in chunks[0].text
    assert "page=2" in response.system_reminder


async def test_recent_page_offsets_the_order(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(
        monkeypatch,
        "list_recent_async",
        ProjectChatSummaryPage(chats=[_summary()], next_cursor="c1"),
        ProjectChatSummaryPage(chats=[_summary("chat_b")], next_cursor=None),
    )

    response = await _tool(recent_limit=1).run(_call(mode="recent", page=2))

    chunks = response.content_chunks or []
    assert [(chunk.id, chunk.order) for chunk in chunks] == [("chat_b", 1)]
    assert response.system_reminder == ""


# ── Sources and citations ─────────────────────────────────────────────────────


async def test_sources_use_the_kb_chunk_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, "search_async", ProjectChatChunkPage(chunks=[_chunk()]))

    response = await _tool().run(_call(mode="search", query="CEO"))

    source = (response.content_chunks or [])[0]
    sections = _parse_chunk(source, SourceFormatConfig().sections)
    assert sections["document"] == 'Chat: "Current CEO of NVIDIA"'
    assert sections["info"].startswith(
        f"Earlier chat in this project (chat_id {NVIDIA_CHAT})"
    )
    assert sections["text"].startswith("[pair 1")
    assert "<em>" not in source.text


async def test_citations_become_one_chat_reference_with_the_chat_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(
        monkeypatch,
        "search_async",
        ProjectChatChunkPage(chunks=[_chunk(index=0), _chunk(index=1)]),
    )

    response = await _tool(chat_url_template="https://app.example/chat/{chat_id}").run(
        _call(mode="search", query="CEO")
    )
    chunks = response.content_chunks or []
    message = add_references_to_message(
        message=_assistant_message("Jensen Huang leads NVIDIA [1][2]."),
        search_context=chunks,
    )[0]

    references = message.references or []
    assert len(references) == 1
    assert references[0].name == 'Chat: "Current CEO of NVIDIA"'
    assert references[0].url == f"https://app.example/chat/{NVIDIA_CHAT}"
    assert not references[0].source_id.startswith("cont_")


async def test_default_chat_link_is_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, "search_async", ProjectChatChunkPage(chunks=[_chunk()]))

    response = await _tool().run(_call(mode="search", query="CEO"))

    assert (response.content_chunks or [])[0].url == f"/chat/{NVIDIA_CHAT}"


async def test_sources_beyond_the_token_budget_are_left_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_text = "word " * 400
    _patch(
        monkeypatch,
        "search_async",
        ProjectChatChunkPage(
            chunks=[_chunk(index=i, text=long_text) for i in range(3)]
        ),
    )

    response = await _tool(max_tokens=1200).run(_call(mode="search", query="CEO"))

    assert len(response.content_chunks or []) == 2
    assert "1 more result(s) were left out" in response.system_reminder


# ── Failures ──────────────────────────────────────────────────────────────────


async def test_outside_a_project_the_tool_reports_an_error() -> None:
    response = await _tool(_event()).run(_call(mode="recent"))

    assert not response.successful


async def test_invalid_mode_returns_the_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    response = await _tool().run(_call(mode="summarise"))

    assert response.successful
    assert '"mode": "search"' in response.content


async def test_api_errors_become_error_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch(monkeypatch, "search_async", RuntimeError("boom"))

    response = await _tool().run(_call(mode="search", query="CEO"))

    assert not response.successful


def _assistant_message(text: str) -> Any:
    from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole

    return ChatMessage(
        id="msg_assistant",
        chat_id=CURRENT_CHAT,
        role=ChatMessageRole.ASSISTANT,
        text=text,
        content=text,
    )


def test_dates_with_an_offset_are_shown_in_utc() -> None:
    from datetime import timedelta, timezone

    from unique_project_chat_search.sources import excerpt_source

    chunk = _chunk().model_copy(
        update={
            "created_at": datetime(
                2026, 11, 24, 16, 17, tzinfo=timezone(timedelta(hours=2))
            )
        }
    )

    assert (
        "2026-11-24 14:17 UTC"
        in excerpt_source(chunk, url_template="/chat/{chat_id}").text
    )
