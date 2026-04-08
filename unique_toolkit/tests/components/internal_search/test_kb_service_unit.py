"""Unit tests for KnowledgeBaseInternalSearchService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit.components.internal_search.knowledge_base.config import (
    KnowledgeBaseInternalSearchConfig,
)
from unique_toolkit.components.internal_search.knowledge_base.schemas import (
    UNSET,
    KnowledgeBaseInternalSearchDeps,
    KnowledgeBaseInternalSearchState,
)
from unique_toolkit.components.internal_search.knowledge_base.service import (
    KnowledgeBaseInternalSearchService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(
    config: KnowledgeBaseInternalSearchConfig | None = None,
    chat_context: MagicMock | None = None,
) -> tuple[KnowledgeBaseInternalSearchService, MagicMock]:
    """Return (service, mock_kb_service)."""
    cfg = config or KnowledgeBaseInternalSearchConfig(scope_ids=["scope-1"])
    svc = KnowledgeBaseInternalSearchService.from_config(cfg)

    mock_kb_svc = AsyncMock()
    mock_sorter = MagicMock()

    svc._dependencies = KnowledgeBaseInternalSearchDeps(
        chunk_relevancy_sorter=mock_sorter,
        knowledge_base_service=mock_kb_svc,
    )
    context = MagicMock()
    context.chat = chat_context
    svc._context = context
    svc.reset_state()
    return svc, mock_kb_svc


# ---------------------------------------------------------------------------
# reset_state — uses KnowledgeBaseInternalSearchState
# ---------------------------------------------------------------------------


@pytest.mark.verified
def test_reset_state__creates_kb_state():
    """
    Purpose: Verifies that reset_state initialises KnowledgeBaseInternalSearchState, not the base class.
    Why this matters: The KB subclass extends state with content_ids and metadata_filter_override;
        using the wrong state type would silently lose those fields.
    Setup summary: After reset_state, assert state is a KnowledgeBaseInternalSearchState instance
        with UNSET as the default metadata_filter_override.
    """
    svc, _ = _make_service()
    assert isinstance(svc._state, KnowledgeBaseInternalSearchState)
    assert svc._state.metadata_filter_override is UNSET


# ---------------------------------------------------------------------------
# _effective_metadata_filter logic
# ---------------------------------------------------------------------------


@pytest.mark.verified
def test_effective_metadata_filter__unset_uses_chat_context_filter():
    """
    Purpose: Verifies that UNSET (default) falls back to the chat context metadata filter.
    Why this matters: The typical flow uses the chat context filter; this is the main
        source of per-user document scoping.
    Setup summary: State with UNSET override and context with a chat filter; assert chat filter returned.
    """
    chat_ctx = MagicMock()
    chat_ctx.metadata_filter = {"key": "value"}
    svc, _ = _make_service(chat_context=chat_ctx)

    assert svc._effective_metadata_filter == {"key": "value"}


@pytest.mark.verified
def test_effective_metadata_filter__explicit_none_override_returns_none():
    """
    Purpose: Verifies that explicitly setting metadata_filter_override=None returns None,
        distinct from UNSET which would fall back to chat context.
    Why this matters: Callers need a way to disable filtering altogether without the chat
        context filter taking over; UNSET vs None must be discriminated.
    Setup summary: State override set to None; assert None is returned regardless of context.
    """
    chat_ctx = MagicMock()
    chat_ctx.metadata_filter = {"key": "value"}
    svc, _ = _make_service(chat_context=chat_ctx)
    svc._state.metadata_filter_override = None

    assert svc._effective_metadata_filter is None


@pytest.mark.verified
def test_effective_metadata_filter__explicit_dict_override_takes_precedence():
    """
    Purpose: Verifies that a dict override is returned instead of the chat context filter.
    Why this matters: Per-call overrides (e.g. from tool invocation params) must win over
        the chat context to allow fine-grained control.
    Setup summary: Override set to {"custom": "filter"}; chat context has different filter;
        assert override is returned.
    """
    chat_ctx = MagicMock()
    chat_ctx.metadata_filter = {"key": "value"}
    svc, _ = _make_service(chat_context=chat_ctx)
    svc._state.metadata_filter_override = {"custom": "filter"}

    assert svc._effective_metadata_filter == {"custom": "filter"}


@pytest.mark.verified
def test_effective_metadata_filter__unset_no_chat_uses_config_filter():
    """
    Purpose: Verifies that UNSET with no chat context falls back to the static config filter.
    Why this matters: KB service can be used outside chat context (e.g. batch jobs);
        the config filter must apply in those cases.
    Setup summary: No chat context (context.chat is None); config has a static metadata_filter;
        assert config filter returned.
    """
    cfg = KnowledgeBaseInternalSearchConfig(
        scope_ids=None,
        metadata_filter={"doc_type": "report"},
    )
    svc, _ = _make_service(config=cfg, chat_context=None)

    assert svc._effective_metadata_filter == {"doc_type": "report"}


# ---------------------------------------------------------------------------
# _search_single_query — routing logic
# ---------------------------------------------------------------------------


@pytest.mark.verified
async def test_search_single_query__uses_scope_ids_when_set(make_chunk):
    """
    Purpose: Verifies that scope_ids are passed to KB search when present in config.
    Why this matters: scope_ids are the primary isolation mechanism; not passing them
        would return results from unintended knowledge bases.
    Setup summary: Config with scope_ids; mock KB service; assert search called with scope_ids.
    """
    cfg = KnowledgeBaseInternalSearchConfig(scope_ids=["kb-1", "kb-2"])
    svc, mock_kb_svc = _make_service(config=cfg)
    mock_kb_svc.search_content_chunks_async = AsyncMock(return_value=[make_chunk("x")])

    await svc._search_single_query(query="hello")

    call_kwargs = mock_kb_svc.search_content_chunks_async.call_args.kwargs
    assert call_kwargs["scope_ids"] == ["kb-1", "kb-2"]
    assert "metadata_filter" not in call_kwargs
    assert "content_ids" not in call_kwargs


@pytest.mark.verified
async def test_search_single_query__uses_metadata_filter_when_no_scope_ids():
    """
    Purpose: Verifies that metadata_filter is passed when scope_ids is None.
    Why this matters: Without scope_ids, filtering falls back to metadata; sending neither
        raises a RuntimeError (next test), so the filter must be forwarded.
    Setup summary: Config with scope_ids=None and a static metadata_filter; assert search
        called with metadata_filter.
    """
    cfg = KnowledgeBaseInternalSearchConfig(
        scope_ids=None, metadata_filter={"type": "policy"}
    )
    svc, mock_kb_svc = _make_service(config=cfg, chat_context=None)
    mock_kb_svc.search_content_chunks_async = AsyncMock(return_value=[])

    await svc._search_single_query(query="policy question")

    call_kwargs = mock_kb_svc.search_content_chunks_async.call_args.kwargs
    assert call_kwargs["metadata_filter"] == {"type": "policy"}
    assert "scope_ids" not in call_kwargs


@pytest.mark.verified
async def test_search_single_query__includes_content_ids_with_metadata_filter():
    """
    Purpose: Verifies that content_ids are forwarded alongside metadata_filter when both are set.
    Why this matters: The KB API requires content_ids to be paired with metadata_filter;
        sending content_ids alone or omitting it silently changes the result set.
    Setup summary: State with content_ids and a config with metadata_filter; assert both
        appear in the call kwargs.
    """
    cfg = KnowledgeBaseInternalSearchConfig(
        scope_ids=None, metadata_filter={"type": "doc"}
    )
    svc, mock_kb_svc = _make_service(config=cfg, chat_context=None)
    svc._state.content_ids = ["doc-1", "doc-2"]
    mock_kb_svc.search_content_chunks_async = AsyncMock(return_value=[])

    await svc._search_single_query(query="question")

    call_kwargs = mock_kb_svc.search_content_chunks_async.call_args.kwargs
    assert call_kwargs["metadata_filter"] == {"type": "doc"}
    assert call_kwargs["content_ids"] == ["doc-1", "doc-2"]


@pytest.mark.verified
async def test_search_single_query__raises_when_neither_scope_ids_nor_filter():
    """
    Purpose: Verifies that a RuntimeError is raised when both scope_ids and metadata_filter
        are absent/None.
    Why this matters: Executing an unscoped KB search would return results from all documents
        for all users — a data-isolation violation.
    Setup summary: Config with scope_ids=None and no filter, no chat context; assert RuntimeError.
    """
    cfg = KnowledgeBaseInternalSearchConfig(scope_ids=None, metadata_filter=None)
    svc, _ = _make_service(config=cfg, chat_context=None)

    with pytest.raises(RuntimeError, match="scope_ids or metadata_filter"):
        await svc._search_single_query(query="unrestricted")


# ---------------------------------------------------------------------------
# Full run() — smoke test
# ---------------------------------------------------------------------------


@pytest.mark.verified
async def test_run__produces_result_from_kb_search(make_chunk, set_runnable_state):
    """
    Purpose: Verifies the full pipeline works end-to-end for KB search.
    Why this matters: KnowledgeBaseInternalSearchService is the entry point for all
        knowledge-base–backed responses; regressions here affect knowledge retrieval quality.
    Setup summary: Service with scope_ids and one query; KB service returns one chunk;
        assert result contains that chunk and debug_info has the search string.
    """
    svc, mock_kb_svc = _make_service()
    set_runnable_state(svc, ["company policy on travel"])
    mock_kb_svc.search_content_chunks_async = AsyncMock(
        return_value=[make_chunk("kb-1")]
    )

    with patch.object(svc, "post_progress_message", new=AsyncMock()):
        result = await svc.run()

    assert len(result.chunks) >= 1
    assert result.debug_info.get("searchStrings") == ["company policy on travel"]
