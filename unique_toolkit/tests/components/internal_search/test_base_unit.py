"""Unit tests for InternalSearchBaseService, InternalSearchConfig, and InternalSearchState."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit._common.chunk_relevancy_sorter.exception import (
    ChunkRelevancySorterException,
)
from unique_toolkit.app.unique_settings import UniqueContext, UniqueSettings
from unique_toolkit.components.internal_search.base.config import InternalSearchConfig
from unique_toolkit.components.internal_search.base.schemas import (
    InternalSearchState,
    SearchStringResult,
)
from unique_toolkit.components.internal_search.base.service import (
    InternalSearchBaseService,
)

# ---------------------------------------------------------------------------
# Minimal concrete implementation for testing the abstract base
# ---------------------------------------------------------------------------


@dataclass
class _FakeDeps:
    chunk_relevancy_sorter: MagicMock


class _ConcreteSearchService(InternalSearchBaseService[_FakeDeps]):
    """Minimal concrete subclass used only in tests."""

    def _make_dependencies(
        self, settings: UniqueSettings, context: UniqueContext
    ) -> _FakeDeps:
        return _FakeDeps(chunk_relevancy_sorter=MagicMock())

    async def _search_single_query(self, *, query: str) -> SearchStringResult:
        return SearchStringResult(query=query, chunks=[])


def _make_service(config: InternalSearchConfig | None = None) -> _ConcreteSearchService:
    cfg = config or InternalSearchConfig()
    svc = _ConcreteSearchService.from_config(cfg)
    svc._context = MagicMock(spec=UniqueContext)
    svc._dependencies = _FakeDeps(chunk_relevancy_sorter=MagicMock())
    svc.reset_state()
    return svc


# ---------------------------------------------------------------------------
# InternalSearchState.get_max_tokens
# ---------------------------------------------------------------------------


@pytest.mark.verified
def test_get_max_tokens__uses_model_tokens_when_set():
    """
    Purpose: Verifies that get_max_tokens scales language_model_max_input_tokens by percentage.
    Why this matters: If the model token budget is ignored, sources could exceed the context window.
    Setup summary: State with 10_000 max input tokens; assert 40% = 4000.
    """
    state = InternalSearchState(
        search_queries=["q"],
        language_model_max_input_tokens=10_000,
    )
    assert state.get_max_tokens(percentage=0.4, fallback=99) == 4_000


@pytest.mark.verified
def test_get_max_tokens__uses_fallback_when_tokens_unset():
    """
    Purpose: Verifies that the fallback is returned when language_model_max_input_tokens is None.
    Why this matters: The service must not crash when model token info is unavailable.
    Setup summary: State with no token limit; assert fallback is returned unchanged.
    """
    state = InternalSearchState(search_queries=["q"])
    assert state.get_max_tokens(percentage=0.5, fallback=30_000) == 30_000


# ---------------------------------------------------------------------------
# InternalSearchConfig defaults and legacy field remapping
# ---------------------------------------------------------------------------


@pytest.mark.verified
def test_config_defaults():
    """
    Purpose: Verifies that InternalSearchConfig has sensible defaults.
    Why this matters: Wrong defaults silently change search behaviour in production.
    Setup summary: Instantiate with no args; spot-check key fields.
    """
    cfg = InternalSearchConfig()
    assert cfg.search_language == "english"
    assert 0.0 <= cfg.percentage_of_input_tokens_for_sources <= 1.0
    assert cfg.max_search_strings >= 1
    assert cfg.score_threshold == 0.0


@pytest.mark.verified
def test_config_limit_default_when_sort_disabled():
    """
    Purpose: Verifies that the default limit is higher when chunk relevancy sort is disabled.
    Why this matters: A higher limit compensates for the lack of resorting by fetching more candidates.
    Setup summary: Config with sort disabled; assert limit equals the 'sort disabled' constant.
    """
    from unique_toolkit._common.chunk_relevancy_sorter.config import (
        ChunkRelevancySortConfig,
    )
    from unique_toolkit.components.internal_search.base.config import (
        DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_DISABLED,
        DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_ENABLED,
    )

    cfg_disabled = InternalSearchConfig(
        chunk_relevancy_sort_config=ChunkRelevancySortConfig(enabled=False)
    )
    cfg_enabled = InternalSearchConfig(
        chunk_relevancy_sort_config=ChunkRelevancySortConfig(enabled=True)
    )
    assert cfg_disabled.limit == DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_DISABLED
    assert cfg_enabled.limit == DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_ENABLED


@pytest.mark.verified
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


@pytest.mark.verified
def test_validate_state__raises_on_empty_queries(language_model_info):
    """
    Purpose: Verifies that run() is blocked when no search queries are set.
    Why this matters: Executing with zero queries would either crash or return empty results
        without a meaningful error to the caller.
    Setup summary: Service with no queries in state; assert ValueError is raised.
    """
    svc = _make_service()
    svc._state.language_model_info = language_model_info
    svc._state.search_queries = []

    with pytest.raises(ValueError, match="at least one search query"):
        svc._validate_state()


@pytest.mark.verified
def test_validate_state__raises_on_missing_language_model_info():
    """
    Purpose: Verifies that run() is blocked when language_model_info is absent.
    Why this matters: Token-window calculation requires model info; missing it silently falls
        back to the config max which may be wrong for the active model.
    Setup summary: Service with queries but no language_model_info; assert ValueError.
    """
    svc = _make_service()
    svc._state.search_queries = ["hello"]
    svc._state.language_model_info = None

    with pytest.raises(ValueError, match="language_model_info"):
        svc._validate_state()


@pytest.mark.verified
def test_validate_state__passes_when_state_is_complete(language_model_info):
    """
    Purpose: Verifies that _validate_state does not raise when all required fields are set.
    Why this matters: A false-positive guard would block valid runs.
    Setup summary: Service with queries and language_model_info; assert no exception raised.
    """
    svc = _make_service()
    svc._state.search_queries = ["hello"]
    svc._state.language_model_info = language_model_info
    svc._validate_state()  # must not raise


# ---------------------------------------------------------------------------
# InternalSearchBaseService._normalise_queries
# ---------------------------------------------------------------------------


@pytest.mark.verified
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


@pytest.mark.verified
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


@pytest.mark.verified
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


@pytest.mark.verified
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
# InternalSearchBaseService._resort_chunks (mocked sorter)
# ---------------------------------------------------------------------------


@pytest.mark.verified
async def test_resort_chunks__returns_sorted_chunks_on_success(make_chunk):
    """
    Purpose: Verifies that _resort_chunks delegates to ChunkRelevancySorter and returns its output.
    Why this matters: Resorting is the primary quality improvement in the pipeline; a silent failure
        to call it would degrade retrieval quality.
    Setup summary: Mock sorter returns two chunks in swapped order; assert order matches mock output.
    """
    svc = _make_service()
    chunks = [make_chunk("a"), make_chunk("b")]
    sorted_chunks = [make_chunk("b"), make_chunk("a")]

    mock_result = MagicMock()
    mock_result.content_chunks = sorted_chunks
    mock_sorter = AsyncMock()
    mock_sorter.run = AsyncMock(return_value=mock_result)
    svc._dependencies.chunk_relevancy_sorter = mock_sorter

    result = await svc._resort_chunks(SearchStringResult(query="q", chunks=chunks))
    assert result == sorted_chunks


@pytest.mark.verified
async def test_resort_chunks__falls_back_to_original_on_sorter_exception(make_chunk):
    """
    Purpose: Verifies that a ChunkRelevancySorterException is caught and original chunks returned.
    Why this matters: Sorter failures must degrade gracefully; the search result should still be
        delivered even if resorting fails.
    Setup summary: Sorter raises ChunkRelevancySorterException; assert original chunks returned.
    """
    svc = _make_service()
    chunks = [make_chunk("x"), make_chunk("y")]

    mock_sorter = AsyncMock()
    mock_sorter.run = AsyncMock(
        side_effect=ChunkRelevancySorterException(
            user_message="fail", error_message="err"
        )
    )
    svc._dependencies.chunk_relevancy_sorter = mock_sorter

    result = await svc._resort_chunks(SearchStringResult(query="q", chunks=chunks))
    assert result == chunks


# ---------------------------------------------------------------------------
# InternalSearchBaseService.run — full pipeline (mocked _search_single_query)
# ---------------------------------------------------------------------------


@pytest.mark.verified
async def test_run__returns_result_with_chunks(make_chunk, language_model_info):
    """
    Purpose: Verifies the full run() pipeline produces an InternalSearchResult with chunks.
    Why this matters: run() is the primary public API; if it returns wrong or empty chunks,
        the chat response will have no sources.
    Setup summary: Service with one query; _search_single_query returns two chunks;
        assert result contains those chunks (modulo token-window picking).
    """
    svc = _make_service()
    svc._state.search_queries = ["test query"]
    svc._state.language_model_info = language_model_info
    svc._state.language_model_max_input_tokens = 128_000

    chunks = [make_chunk("1", "text one"), make_chunk("2", "text two")]
    svc._search_single_query = AsyncMock(  # type: ignore[method-assign]
        return_value=SearchStringResult(query="test query", chunks=chunks)
    )

    with patch.object(svc, "post_progress_message", new=AsyncMock()):
        result = await svc.run()

    assert len(result.chunks) > 0
    assert "searchStrings" in result.debug_info


@pytest.mark.verified
async def test_run__raises_when_state_invalid(language_model_info):
    """
    Purpose: Verifies that run() raises ValueError before calling any search when state is incomplete.
    Why this matters: Without this guard, partial state could cause confusing downstream errors.
    Setup summary: Service with no search queries; assert ValueError is raised immediately.
    """
    svc = _make_service()
    svc._state.language_model_info = language_model_info

    with pytest.raises(ValueError):
        await svc.run()
