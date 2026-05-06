from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Self

from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.content import (
    ContentChunk,
    merge_content_chunks,
    pick_content_chunks_for_token_window,
    sort_content_chunks,
)
from unique_toolkit.experimental.components.internal_search.base.schemas import (
    InternalSearchResult,
    SearchStringResult,
)
from unique_toolkit.experimental.components.internal_search.base.utils import (
    append_metadata_in_chunks,
    interleave_search_results_round_robin,
)
from unique_toolkit.experimental.components.internal_search.post_processing.config import (
    PostProcessorConfig,
)

if TYPE_CHECKING:
    from unique_toolkit._common.chunk_relevancy_sorter.service import (
        ChunkRelevancySorter,
    )
    from unique_toolkit.language_model.infos import LanguageModelInfo

_logger = logging.getLogger(__name__)


class InternalSearchPostProcessor:
    """Rerank, window, and sort raw chunks from InternalSearchResult.

    Intentionally decoupled from the search service so callers can apply only
    the steps they need. The search service is a pure retrieval primitive;
    this class owns the post-retrieval pipeline.

    **Reranking contract** (``chunk_relevancy_sort_config.enabled=True``):

    - ``query_text=None`` (default): each query's chunks are reranked against
      that query's own text, then the reranked groups are interleaved.
      Works for single-query and multi-query results without extra wiring.
    - ``query_text="some text"``: the entire merged pool is reranked against
      the provided text. Use when search strings are reformulations of the same
      user intent and you want whole-list scoring against the original message.
      For a single-query result this is equivalent to per-query rerank with the
      override text — the distinction only matters for multi-query results.

    Typical usage::

        from unique_toolkit.experimental.components.internal_search import (
            KnowledgeBaseInternalSearchService,
            KnowledgeBaseInternalSearchConfig,
            InternalSearchPostProcessor,
            PostProcessorConfig,
        )

        search_service = KnowledgeBaseInternalSearchService.from_config(search_config)
        processor = InternalSearchPostProcessor.from_settings(settings, config=post_config)

        search_service.bind_settings(settings)
        search_service.state.search_queries = ["my query"]
        result = await search_service.run()

        chunks = await processor.process(result, model_info=model_info)
    """

    def __init__(
        self,
        config: PostProcessorConfig,
        *,
        chunk_relevancy_sorter: ChunkRelevancySorter | None = None,
    ) -> None:
        self._config = config
        self._sorter = chunk_relevancy_sorter

    @classmethod
    def from_settings(
        cls, settings: UniqueSettings, *, config: PostProcessorConfig
    ) -> Self:
        """Create a processor bound to settings.

        Instantiates a ChunkRelevancySorter only when chunk_relevancy_sort_config
        is enabled, avoiding unnecessary API clients.
        """
        sorter: ChunkRelevancySorter | None = None
        if config.chunk_relevancy_sort_config.enabled:
            from unique_toolkit.services import UniqueServiceFactory

            sorter = UniqueServiceFactory(settings=settings).chunk_relevancy_sorter()
        return cls(config=config, chunk_relevancy_sorter=sorter)

    async def process(
        self,
        result: InternalSearchResult,
        *,
        query_text: str | None = None,
        model_info: LanguageModelInfo | None = None,
    ) -> list[ContentChunk]:
        """Apply reranking, token windowing, sorting, and metadata templating.

        Args:
            result: Raw output from InternalSearchBaseService.run().
            query_text: Controls reranking behaviour when
                ``chunk_relevancy_sort_config`` is enabled:

                - ``None`` (default): per-query rerank — each query's chunks are
                  scored against that query's own text, then interleaved.
                - ``str``: whole-list override — the entire merged chunk pool is
                  reranked against the provided text. Useful when all search
                  strings are reformulations of the same user intent.

            model_info: When provided, token window is computed as
                ``percentage_of_input_tokens_for_sources * model_info.token_limits.token_limit_input``.
                Falls back to ``max_tokens_for_sources`` when None.

        Returns:
            Post-processed chunks, ready to be used as sources.
        """
        chunks = await self._apply_reranking(result, query_text=query_text)

        token_limit = self._resolve_token_limit(model_info)
        chunks = pick_content_chunks_for_token_window(
            chunks,
            token_limit,
            model_info=model_info,
        )

        chunks = (
            sort_content_chunks(chunks)
            if self._config.chunked_sources
            else merge_content_chunks(chunks)
        )

        if self._config.metadata_chunk_sections:
            chunks = append_metadata_in_chunks(
                chunks, self._config.metadata_chunk_sections
            )

        return chunks

    async def _apply_reranking(
        self,
        result: InternalSearchResult,
        *,
        query_text: str | None,
    ) -> list[ContentChunk]:
        if not self._config.chunk_relevancy_sort_config.enabled or self._sorter is None:
            return list(result.chunks)

        if query_text is not None:
            # Whole-list override: rerank the already-interleaved flat list.
            return await self._rerank(list(result.chunks), query_text=query_text)

        # Per-query: rerank each group against its own query, then re-interleave.
        reranked: list[SearchStringResult] = []
        for sr in result.search_string_results:
            ranked_chunks = await self._rerank(list(sr.chunks), query_text=sr.query)
            reranked.append(SearchStringResult(query=sr.query, chunks=ranked_chunks))

        if len(reranked) > 1:
            reranked = interleave_search_results_round_robin(reranked)

        return [chunk for sr in reranked for chunk in sr.chunks]

    async def _rerank(
        self, chunks: list[ContentChunk], *, query_text: str
    ) -> list[ContentChunk]:
        assert self._sorter is not None
        from unique_toolkit._common.chunk_relevancy_sorter.exception import (
            ChunkRelevancySorterException,
        )

        try:
            reranked = await self._sorter.run(
                input_text=query_text,
                chunks=chunks,
                config=self._config.chunk_relevancy_sort_config,
            )
            return reranked.content_chunks
        except ChunkRelevancySorterException as e:
            _logger.warning(
                "Reranking failed for query %r: %s", query_text, e.error_message
            )
            return chunks

    def _resolve_token_limit(self, model_info: LanguageModelInfo | None) -> int:
        if model_info is not None:
            return int(
                model_info.token_limits.token_limit_input
                * self._config.percentage_of_input_tokens_for_sources
            )
        return self._config.max_tokens_for_sources


__all__ = ["InternalSearchPostProcessor"]
