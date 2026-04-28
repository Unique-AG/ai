"""Unit tests for InternalSearchPostProcessor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.chunk_relevancy_sorter.exception import (
    ChunkRelevancySorterException,
)
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.experimental.components.internal_search.base.schemas import (
    InternalSearchResult,
    SearchStringResult,
)
from unique_toolkit.experimental.components.internal_search.post_processing.config import (
    PostProcessorConfig,
)
from unique_toolkit.experimental.components.internal_search.post_processing.service import (
    InternalSearchPostProcessor,
)
from unique_toolkit.language_model.infos import LanguageModelInfo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(chunk_id: str, text: str = "x" * 100) -> ContentChunk:
    return ContentChunk(chunk_id=chunk_id, text=text, start_page=1, end_page=1)


def _make_result(
    *query_chunk_pairs: tuple[str, list[str]],
) -> InternalSearchResult:
    """Build an InternalSearchResult with per-query structure.

    Each pair is (query_text, [chunk_id, ...]).
    chunks is the flat concatenation; search_string_results holds the per-query groups.
    """
    search_string_results = [
        SearchStringResult(query=q, chunks=[_make_chunk(cid) for cid in cids])
        for q, cids in query_chunk_pairs
    ]
    flat_chunks = [chunk for sr in search_string_results for chunk in sr.chunks]
    return InternalSearchResult(
        chunks=flat_chunks,
        search_string_results=search_string_results,
        debug_info={},
    )


def _single_result(*chunk_ids: str) -> InternalSearchResult:
    """Convenience: single-query result."""
    return _make_result(("query", list(chunk_ids)))


def _config(
    *,
    max_tokens: int = 100_000,
    pct: float = 0.4,
    chunked: bool = True,
    sort_enabled: bool = False,
    metadata_sections: dict[str, str] | None = None,
) -> PostProcessorConfig:
    sort_cfg = ChunkRelevancySortConfig(enabled=sort_enabled)
    return PostProcessorConfig(
        max_tokens_for_sources=max_tokens,
        percentage_of_input_tokens_for_sources=pct,
        chunked_sources=chunked,
        chunk_relevancy_sort_config=sort_cfg,
        metadata_chunk_sections=metadata_sections or {},
    )


def _mock_sorter(return_chunks: list[ContentChunk]) -> MagicMock:
    sorter = MagicMock()
    sorter.run = AsyncMock(return_value=MagicMock(content_chunks=return_chunks))
    return sorter


# ---------------------------------------------------------------------------
# Token-limit fallback
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_token_limit_uses_max_tokens_when_no_model_info():
    """Falls back to max_tokens_for_sources when model_info is None."""
    processor = InternalSearchPostProcessor(config=_config(max_tokens=1))
    result = _single_result("c1", "c2", "c3")

    chunks = await processor.process(result)

    assert len(chunks) <= len(result.chunks)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_token_limit_uses_model_info_percentage_when_provided():
    """Uses percentage_of_input_tokens_for_sources × token_limit_input when model_info provided."""
    model_info = LanguageModelInfo(
        name="gpt-4o", token_limit_input=10, token_limit_output=4096
    )
    processor = InternalSearchPostProcessor(config=_config(pct=0.0, max_tokens=100_000))
    result = _single_result("c1", "c2")

    chunks = await processor.process(result, model_info=model_info)

    assert isinstance(chunks, list)
    assert len(chunks) <= len(result.chunks)


# ---------------------------------------------------------------------------
# Q2: Per-query rerank — each query's chunks scored against its own text
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_per_query_rerank__each_query_scored_against_its_own_text():
    """Per-query: chunks from query A are ranked against query A, not query B."""
    call_log: list[str] = []

    async def fake_run(*, input_text: str, chunks, config):
        call_log.append(input_text)
        return MagicMock(content_chunks=chunks)

    sorter = MagicMock()
    sorter.run = fake_run

    result = _make_result(("alpha query", ["a1", "a2"]), ("beta query", ["b1", "b2"]))
    processor = InternalSearchPostProcessor(
        config=_config(sort_enabled=True),
        chunk_relevancy_sorter=sorter,
    )

    await processor.process(result, query_text=None)

    assert "alpha query" in call_log
    assert "beta query" in call_log
    # The queries used for scoring must match the retrieval queries, not each other.
    assert call_log.count("alpha query") >= 1
    assert call_log.count("beta query") >= 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_per_query_rerank__single_query_uses_that_query_text():
    """Single-query result with query_text=None uses sr.query for reranking."""
    used_texts: list[str] = []

    async def fake_run(*, input_text: str, chunks, config):
        used_texts.append(input_text)
        return MagicMock(content_chunks=chunks)

    sorter = MagicMock()
    sorter.run = fake_run

    result = _make_result(("my precise query", ["c1", "c2"]))
    processor = InternalSearchPostProcessor(
        config=_config(sort_enabled=True),
        chunk_relevancy_sorter=sorter,
    )

    await processor.process(result, query_text=None)

    assert used_texts == ["my precise query"]


# ---------------------------------------------------------------------------
# Q3: query_text override — whole-list rerank against provided text
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_query_text_override__whole_list_scored_against_override():
    """query_text override: all chunks ranked against the override, not per-query."""
    used_texts: list[str] = []

    async def fake_run(*, input_text: str, chunks, config):
        used_texts.append(input_text)
        return MagicMock(content_chunks=chunks)

    sorter = MagicMock()
    sorter.run = fake_run

    result = _make_result(("query A", ["a1"]), ("query B", ["b1"]))
    processor = InternalSearchPostProcessor(
        config=_config(sort_enabled=True),
        chunk_relevancy_sorter=sorter,
    )

    await processor.process(result, query_text="original user message")

    # Exactly one rerank call against the override text, NOT query A or query B.
    assert used_texts == ["original user message"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_query_text_override__single_query_uses_override_not_sr_query():
    """Single-query + query_text override → override text is used, not sr.query."""
    used_texts: list[str] = []

    async def fake_run(*, input_text: str, chunks, config):
        used_texts.append(input_text)
        return MagicMock(content_chunks=chunks)

    sorter = MagicMock()
    sorter.run = fake_run

    result = _make_result(("internal sub-query", ["c1"]))
    processor = InternalSearchPostProcessor(
        config=_config(sort_enabled=True),
        chunk_relevancy_sorter=sorter,
    )

    await processor.process(result, query_text="user's original question")

    assert used_texts == ["user's original question"]


# ---------------------------------------------------------------------------
# Exception swallow in per-query loop
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rerank_exception_per_query__failing_query_falls_back_original_chunks():
    """ChunkRelevancySorterException on one query does not discard its chunks."""
    sorter = MagicMock()
    sorter.run = AsyncMock(
        side_effect=ChunkRelevancySorterException("boom", "internal error")
    )

    result = _make_result(("q1", ["c1", "c2"]))
    processor = InternalSearchPostProcessor(
        config=_config(sort_enabled=True, max_tokens=100_000),
        chunk_relevancy_sorter=sorter,
    )

    chunks = await processor.process(result, query_text=None)

    assert len(chunks) == 2


# ---------------------------------------------------------------------------
# chunked_sources toggle
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_chunked_sources_true_calls_sort():
    """chunked_sources=True calls sort_content_chunks, not merge."""
    with (
        patch(
            "unique_toolkit.experimental.components.internal_search.post_processing.service.sort_content_chunks"
        ) as mock_sort,
        patch(
            "unique_toolkit.experimental.components.internal_search.post_processing.service.merge_content_chunks"
        ) as mock_merge,
    ):
        mock_sort.return_value = []
        processor = InternalSearchPostProcessor(config=_config(chunked=True))
        await processor.process(_single_result("c1"))

    mock_sort.assert_called_once()
    mock_merge.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_chunked_sources_false_calls_merge():
    """chunked_sources=False calls merge_content_chunks, not sort."""
    with (
        patch(
            "unique_toolkit.experimental.components.internal_search.post_processing.service.sort_content_chunks"
        ) as mock_sort,
        patch(
            "unique_toolkit.experimental.components.internal_search.post_processing.service.merge_content_chunks"
        ) as mock_merge,
    ):
        mock_merge.return_value = []
        processor = InternalSearchPostProcessor(config=_config(chunked=False))
        await processor.process(_single_result("c1"))

    mock_merge.assert_called_once()
    mock_sort.assert_not_called()


# ---------------------------------------------------------------------------
# Q8: metadata_chunk_sections applied as final step
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_metadata_sections_applied_last():
    """metadata_chunk_sections is applied after sort/merge."""
    chunk = _make_chunk("c1", text="base text")
    chunk.metadata = MagicMock()
    chunk.metadata.model_dump.return_value = {"source": "doc.pdf"}

    result = InternalSearchResult(
        chunks=[chunk],
        search_string_results=[SearchStringResult(query="q", chunks=[chunk])],
        debug_info={},
    )
    processor = InternalSearchPostProcessor(
        config=_config(metadata_sections={"source": "<|src|>{}<|/src|>"})
    )

    chunks = await processor.process(result)

    assert len(chunks) == 1
    assert "<|src|>doc.pdf<|/src|>" in chunks[0].text
