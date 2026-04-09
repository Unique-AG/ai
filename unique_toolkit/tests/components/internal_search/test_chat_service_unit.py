"""Unit tests for ChatInternalSearchService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit.components.internal_search.base.config import InternalSearchConfig
from unique_toolkit.components.internal_search.base.schemas import (
    InternalSearchState,
    SearchStringResult,
)
from unique_toolkit.components.internal_search.chat.schemas import (
    ChatInternalSearchDeps,
)
from unique_toolkit.components.internal_search.chat.service import (
    ChatInternalSearchService,
)
from unique_toolkit.content.schemas import ContentSearchType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(
    config: InternalSearchConfig | None = None,
    chat_context: MagicMock | None = None,
) -> tuple[ChatInternalSearchService, MagicMock, MagicMock]:
    """Return (service, mock_chat_service, mock_sorter)."""
    cfg = config or InternalSearchConfig()
    svc = ChatInternalSearchService.from_config(cfg)

    mock_chat_svc = AsyncMock()
    mock_sorter = MagicMock()

    svc._dependencies = ChatInternalSearchDeps(
        chunk_relevancy_sorter=mock_sorter,
        chat_service=mock_chat_svc,
    )
    context = MagicMock()
    context.chat = chat_context if chat_context is not None else MagicMock()
    svc._context = context
    svc.reset_state()
    return svc, mock_chat_svc, mock_sorter


# ---------------------------------------------------------------------------
# _make_dependencies — requires chat context
# ---------------------------------------------------------------------------


@pytest.mark.verified
def test_make_dependencies__raises_without_chat_context():
    """
    Purpose: Verifies that _make_dependencies raises RuntimeError when chat context is absent.
    Why this matters: ChatInternalSearchService is only valid inside a chat session;
        attempting to bind without one would silently produce a broken service.
    Setup summary: bind_settings called with a settings object whose context has no chat;
        assert RuntimeError is raised.
    """
    svc = ChatInternalSearchService.from_config(InternalSearchConfig())
    mock_context = MagicMock()
    mock_context.chat = None
    mock_settings = MagicMock()
    mock_settings.context = mock_context

    with pytest.raises(RuntimeError, match="chat context"):
        svc.bind_settings(mock_settings)


# ---------------------------------------------------------------------------
# _search_single_query — delegates correctly to ChatService
# ---------------------------------------------------------------------------


@pytest.mark.verified
def test_reset_state__creates_base_state():
    """
    Purpose: Verifies that reset_state initialises a valid InternalSearchState.
    Why this matters: The state must be ready for use before any search query is issued.
    Setup summary: After reset_state, assert state is an InternalSearchState with empty queries.
    """
    svc, _, _ = _make_service()
    assert isinstance(svc._state, InternalSearchState)
    assert svc._state.search_queries == []


@pytest.mark.verified
async def test_search_single_query__calls_chat_service_with_correct_args(make_chunk):
    """
    Purpose: Verifies that _search_single_query passes all config parameters to ChatService.
    Why this matters: Misconfigured search calls (wrong type, limit, language) silently return
        wrong results; the config must be forwarded exactly.
    Setup summary: Mock chat service returns two chunks; assert called with config values.
    """
    cfg = InternalSearchConfig(
        search_type=ContentSearchType.VECTOR,
        limit=50,
        search_language="german",
        score_threshold=0.3,
    )
    svc, mock_chat_svc, _ = _make_service(config=cfg)

    chunks = [make_chunk("a"), make_chunk("b")]
    mock_chat_svc.search_content_chunks_async = AsyncMock(return_value=chunks)

    result = await svc._search_single_query(query="my query")

    mock_chat_svc.search_content_chunks_async.assert_called_once_with(
        search_string="my query",
        search_type=ContentSearchType.VECTOR,
        limit=50,
        reranker_config=cfg.reranker_config,
        search_language="german",
        score_threshold=0.3,
        content_ids=None,
    )
    assert result == SearchStringResult(query="my query", chunks=chunks)


@pytest.mark.verified
async def test_search_single_query__forwards_content_ids_when_set():
    """
    Purpose: Verifies that content_ids from the base state are forwarded to ChatService.
    Why this matters: content_ids is the mechanism for scoping chat searches to specific
        uploaded files; not forwarding it silently ignores the caller's intent.
    Setup summary: State with two content IDs; assert ChatService receives them unchanged.
    """
    svc, mock_chat_svc, _ = _make_service()
    svc._state.content_ids = ["file-1", "file-2"]
    mock_chat_svc.search_content_chunks_async = AsyncMock(return_value=[])

    await svc._search_single_query(query="uploaded file query")

    call_kwargs = mock_chat_svc.search_content_chunks_async.call_args.kwargs
    assert call_kwargs["content_ids"] == ["file-1", "file-2"]


@pytest.mark.verified
async def test_search_single_query__returns_empty_chunks_on_no_results():
    """
    Purpose: Verifies that an empty chunk list from ChatService produces an empty SearchStringResult.
    Why this matters: Empty results are valid (no matching documents); they must not cause a crash.
    Setup summary: Mock chat service returns []; assert SearchStringResult has empty chunks.
    """
    svc, mock_chat_svc, _ = _make_service()
    mock_chat_svc.search_content_chunks_async = AsyncMock(return_value=[])

    result = await svc._search_single_query(query="nothing here")

    assert result.chunks == []
    assert result.query == "nothing here"


# ---------------------------------------------------------------------------
# Full run() — smoke test through the pipeline
# ---------------------------------------------------------------------------


@pytest.mark.verified
async def test_run__produces_result_from_chat_search(make_chunk, set_runnable_state):
    """
    Purpose: Verifies that the full pipeline (run → search → finalize) works end-to-end.
    Why this matters: ChatInternalSearchService is the primary integration point for chat-based
        search; regressions here directly affect user-facing responses.
    Setup summary: Service with one query; chat service returns one chunk; assert result has
        that chunk and debug_info contains the search string.
    """
    svc, mock_chat_svc, _ = _make_service()
    set_runnable_state(svc, ["what is AI?"])
    mock_chat_svc.search_content_chunks_async = AsyncMock(
        return_value=[make_chunk("c1")]
    )

    with patch.object(svc, "post_progress_message", new=AsyncMock()):
        result = await svc.run()

    assert len(result.chunks) >= 1
    assert result.debug_info.get("searchStrings") == ["what is AI?"]
