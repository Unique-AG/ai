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
        """Apply reranking, token windowing, and sorting to raw search chunks.

        Args:
            result: Raw output from InternalSearchBaseService.run().
            query_text: The original search query, required for chunk relevancy sorting.
                Reranking is skipped when None even if chunk_relevancy_sort_config is enabled.
            model_info: When provided, token window is computed as
                ``percentage_of_input_tokens_for_sources * model_info.token_limits.token_limit_input``.
                Falls back to ``max_tokens_for_sources`` when None.

        Returns:
            Post-processed chunks, ready to be used as sources.
        """
        chunks = list(result.chunks)

        if self._config.chunk_relevancy_sort_config.enabled:
            if query_text is None:
                _logger.warning(
                    "chunk_relevancy_sort_config is enabled but query_text was not "
                    "provided — reranking skipped. Pass query_text to process() to enable it."
                )
            elif self._sorter is not None:
                chunks = await self._rerank(chunks, query_text=query_text)

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

        return chunks

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
        except ChunkRelevancySorterException:
            return chunks

    def _resolve_token_limit(self, model_info: LanguageModelInfo | None) -> int:
        if model_info is not None:
            return int(
                model_info.token_limits.token_limit_input
                * self._config.percentage_of_input_tokens_for_sources
            )
        return self._config.max_tokens_for_sources


__all__ = ["InternalSearchPostProcessor"]
