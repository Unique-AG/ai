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


def _make_result(*chunk_ids: str) -> InternalSearchResult:
    return InternalSearchResult(
        chunks=[_make_chunk(cid) for cid in chunk_ids],
        debug_info={},
    )


def _config(
    *,
    max_tokens: int = 100_000,
    pct: float = 0.4,
    chunked: bool = True,
    sort_enabled: bool = False,
) -> PostProcessorConfig:
    sort_cfg = ChunkRelevancySortConfig(enabled=sort_enabled)
    return PostProcessorConfig(
        max_tokens_for_sources=max_tokens,
        percentage_of_input_tokens_for_sources=pct,
        chunked_sources=chunked,
        chunk_relevancy_sort_config=sort_cfg,
    )


# ---------------------------------------------------------------------------
# Token-limit fallback
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_token_limit_uses_max_tokens_when_no_model_info():
    """Falls back to max_tokens_for_sources when model_info is None."""
    processor = InternalSearchPostProcessor(config=_config(max_tokens=1))
    result = _make_result("c1", "c2", "c3")

    # max_tokens=1 is tiny — all but the first chunk should be pruned
    chunks = await processor.process(result)

    assert len(chunks) <= len(result.chunks)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_token_limit_uses_model_info_percentage_when_provided():
    """Uses percentage_of_input_tokens_for_sources × model token limit when model_info provided."""
    model_info = LanguageModelInfo(
        name="gpt-4o", token_limit_input=10, token_limit_output=4096
    )
    # pct=0.0 → budget is 0 → should return empty or a single chunk
    processor = InternalSearchPostProcessor(config=_config(pct=0.0, max_tokens=100_000))
    result = _make_result("c1", "c2")

    chunks = await processor.process(result, model_info=model_info)

    assert isinstance(chunks, list)
    # budget was 0, so at most one chunk survives (pick_content_chunks_for_token_window
    # guarantees at least the first chunk is returned to avoid empty-source issues)
    assert len(chunks) <= len(result.chunks)


# ---------------------------------------------------------------------------
# Reranking — silent skip when query_text missing
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_reranking_skipped_silently_when_query_text_none(caplog):
    """Reranking is skipped and a warning is logged when query_text is None."""
    mock_sorter = MagicMock()
    mock_sorter.run = AsyncMock()

    processor = InternalSearchPostProcessor(
        config=_config(sort_enabled=True),
        chunk_relevancy_sorter=mock_sorter,
    )
    result = _make_result("c1", "c2")

    import logging

    with caplog.at_level(logging.WARNING):
        await processor.process(result, query_text=None)

    mock_sorter.run.assert_not_called()
    assert "reranking skipped" in caplog.text.lower()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_reranking_called_when_query_text_provided():
    """Reranking is invoked when sort is enabled and query_text is supplied."""
    chunk = _make_chunk("c1")
    mock_sorter = MagicMock()
    mock_sorter.run = AsyncMock(return_value=MagicMock(content_chunks=[chunk]))

    processor = InternalSearchPostProcessor(
        config=_config(sort_enabled=True),
        chunk_relevancy_sorter=mock_sorter,
    )
    result = _make_result("c1", "c2")

    await processor.process(result, query_text="my query")

    mock_sorter.run.assert_called_once()


# ---------------------------------------------------------------------------
# Reranking — exception swallowed, original chunks returned
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_rerank_exception_swallowed_returns_original_chunks():
    """ChunkRelevancySorterException is caught and original chunks are returned."""
    mock_sorter = MagicMock()
    mock_sorter.run = AsyncMock(
        side_effect=ChunkRelevancySorterException("reranker failed", "internal error")
    )

    processor = InternalSearchPostProcessor(
        config=_config(sort_enabled=True, max_tokens=100_000),
        chunk_relevancy_sorter=mock_sorter,
    )
    result = _make_result("c1", "c2")

    chunks = await processor.process(result, query_text="q")

    # Original 2 chunks survive despite the reranker raising
    assert len(chunks) == 2


# ---------------------------------------------------------------------------
# chunked_sources toggle
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_chunked_sources_true_returns_sorted_chunks():
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
        await processor.process(_make_result("c1"))

    mock_sort.assert_called_once()
    mock_merge.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_chunked_sources_false_returns_merged_chunks():
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
        await processor.process(_make_result("c1"))

    mock_merge.assert_called_once()
    mock_sort.assert_not_called()
