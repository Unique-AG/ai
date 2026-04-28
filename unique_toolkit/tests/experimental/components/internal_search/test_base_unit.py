"""Unit tests for InternalSearchBaseService, InternalSearchConfig, and InternalSearchState."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings
from unique_toolkit.experimental.components.internal_search.base.config import (
    DEFAULT_LIMIT,
    InternalSearchConfig,
)
from unique_toolkit.experimental.components.internal_search.base.schemas import (
    SearchStringResult,
)
from unique_toolkit.experimental.components.internal_search.base.service import (
    InternalSearchBaseService,
)

# ---------------------------------------------------------------------------
# Minimal concrete implementation for testing the abstract base
# ---------------------------------------------------------------------------


@dataclass
class _FakeDeps:
    pass


class _ConcreteSearchService(InternalSearchBaseService[_FakeDeps]):
    """Minimal concrete subclass used only in tests."""

    def _make_dependencies(
        self, settings: UniqueSettings, context: UniqueContext
    ) -> _FakeDeps:
        return _FakeDeps()

    async def _search_single_query(self, *, query: str) -> SearchStringResult:
        return SearchStringResult(query=query, chunks=[])


def _make_service(config: InternalSearchConfig | None = None) -> _ConcreteSearchService:
    cfg = config or InternalSearchConfig()
    svc = _ConcreteSearchService.from_config(cfg)
    svc._context = MagicMock(spec=UniqueContext)
    svc._dependencies = _FakeDeps()
    svc.reset_state()
    return svc


@pytest.mark.ai
def test_bind_settings__uses_settings_context_and_resets_state():
    """
    Purpose: Verifies that bind_settings preserves the full request context from settings.
    Why this matters: Rebuilding context from settings can drop chat context, which breaks
        chat-aware internal-search services.
    Setup summary: Service with populated state and a settings object carrying a context;
        bind_settings should use that exact context and reset the state.
    """
    svc = _make_service()
    existing_context = MagicMock(spec=UniqueContext)
    settings = MagicMock(spec=UniqueSettings)
    settings.context = existing_context
    svc._state.search_queries = ["stale"]

    svc.bind_settings(settings)

    assert svc.context is existing_context
    assert svc.state.search_queries == []


# ---------------------------------------------------------------------------
# InternalSearchConfig defaults
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_config_defaults():
    """
    Purpose: Verifies that InternalSearchConfig has sensible retrieval-only defaults.
    Why this matters: Wrong defaults silently change search behaviour in production.
    Setup summary: Instantiate with no args; spot-check key fields.
    """
    cfg = InternalSearchConfig()
    assert cfg.search_language == "english"
    assert cfg.max_search_strings >= 1
    assert cfg.score_threshold == 0.0
    assert cfg.limit == DEFAULT_LIMIT


@pytest.mark.ai
def test_config_legacy_field_remapping():
    """
    Purpose: Verifies that the deprecated ftsSearchLanguage key is migrated to searchLanguage.
    Why this matters: Old tool configs stored the legacy key; dropping support would silently revert
        language to the default without an error.
    Setup summary: Construct config dict with ftsSearchLanguage; assert search_language is set.
    """
    cfg = InternalSearchConfig.model_validate({"ftsSearchLanguage": "german"})
    assert cfg.search_language == "german"


# ---------------------------------------------------------------------------
# InternalSearchBaseService._validate_state
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_validate_state__raises_on_empty_queries():
    """
    Purpose: Verifies that run() is blocked when no search queries are set.
    Why this matters: Executing with zero queries would either crash or return empty results
        without a meaningful error to the caller.
    Setup summary: Service with no queries in state; assert ValueError is raised.
    """
    svc = _make_service()
    svc._state.search_queries = []

    with pytest.raises(ValueError, match="at least one search query"):
        svc._validate_state()


@pytest.mark.ai
def test_validate_state__passes_when_state_is_complete():
    """
    Purpose: Verifies that _validate_state does not raise when required fields are set.
    Why this matters: A false-positive guard would block valid runs.
    Setup summary: Service with queries; assert no exception raised.
    """
    svc = _make_service()
    svc._state.search_queries = ["hello"]
    svc._validate_state()  # must not raise


# ---------------------------------------------------------------------------
# InternalSearchBaseService._normalise_queries
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_normalise_queries__cleans_and_deduplicates():
    """
    Purpose: Verifies that operator cleanup and deduplication both apply before truncation.
    Why this matters: Sending duplicate or operator-laden strings wastes search quota and
        may distort round-robin interleaving.
    Setup summary: Three queries with operators and one duplicate; expect two cleaned strings.
    """
    svc = _make_service()
    queries = [
        "+(topic) overview --QDF=1",
        "topic overview",  # same after cleaning
        "+(another) query",
    ]
    result = svc._normalise_queries(queries)
    assert result == ["topic overview", "another query"]


@pytest.mark.ai
def test_normalise_queries__respects_max_search_strings():
    """
    Purpose: Verifies that output is capped at max_search_strings.
    Why this matters: Exceeding the cap could overwhelm the search backend or hit rate limits.
    Setup summary: Config with max_search_strings=2 and three distinct queries; assert only 2 returned.
    """
    cfg = InternalSearchConfig(max_search_strings=2)
    svc = _make_service(cfg)
    result = svc._normalise_queries(["alpha", "beta", "gamma"])
    assert result == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# InternalSearchBaseService._collect_results
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_collect_results__filters_out_exceptions(make_chunk):
    """
    Purpose: Verifies that exceptions in gathered results are skipped, not re-raised.
    Why this matters: One failing search query must not abort the entire run; partial results
        are better than none.
    Setup summary: Mixed list of one good result and one exception; assert only good result returned.
    """
    svc = _make_service()
    good = SearchStringResult(query="q1", chunks=[make_chunk("a")])
    result = svc._collect_results([good, RuntimeError("search failed")], ["q1", "q2"])
    assert result == [good]


@pytest.mark.ai
def test_collect_results__all_failures_returns_empty():
    """
    Purpose: Verifies that all-failed results produce an empty list rather than a crash.
    Why this matters: Downstream code must handle empty found list gracefully.
    Setup summary: Two exception results; assert empty list returned.
    """
    svc = _make_service()
    result = svc._collect_results([ValueError("x"), ValueError("y")], ["q1", "q2"])
    assert result == []


# ---------------------------------------------------------------------------
# InternalSearchBaseService.run — full pipeline (mocked _search_single_query)
# ---------------------------------------------------------------------------


@pytest.mark.ai
async def test_run__returns_result_with_chunks(make_chunk):
    """
    Purpose: Verifies the full run() pipeline produces an InternalSearchResult with chunks.
    Why this matters: run() is the primary public API; if it returns wrong or empty chunks,
        the chat response will have no sources.
    Setup summary: Service with one query; _search_single_query returns two chunks;
        assert result contains those chunks.
    """
    svc = _make_service()
    svc._state.search_queries = ["test query"]

    chunks = [make_chunk("1", "text one"), make_chunk("2", "text two")]
    svc._search_single_query = AsyncMock(  # type: ignore[method-assign]
        return_value=SearchStringResult(query="test query", chunks=chunks)
    )

    with patch.object(svc, "post_progress_message", new=AsyncMock()):
        result = await svc.run()

    assert len(result.chunks) > 0
    assert "searchStrings" in result.debug_info


@pytest.mark.ai
async def test_run__raises_when_state_invalid():
    """
    Purpose: Verifies that run() raises ValueError before calling any search when state is incomplete.
    Why this matters: Without this guard, partial state could cause confusing downstream errors.
    Setup summary: Service with no search queries; assert ValueError is raised immediately.
    """
    svc = _make_service()

    with pytest.raises(ValueError):
        await svc.run()
