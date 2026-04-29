"""Internal search component — retrieval services and post-processing pipeline.

!!! warning "Experimental"
    This subpackage lives under :mod:`unique_toolkit.experimental` and its
    API may change between minor releases.

Provides framework-agnostic knowledge-base and chat search services, plus an
optional post-processing pipeline for reranking and token-budget windowing.

The search services are pure retrieval primitives: they return all matching
chunks up to the configured ``limit``. Post-retrieval steps (reranking, token
windowing, sorting) are handled separately by
:class:`InternalSearchPostProcessor`.

Typical usage::

    from unique_toolkit.experimental.components.internal_search import (
        KnowledgeBaseInternalSearchService,
        KnowledgeBaseInternalSearchConfig,
        InternalSearchPostProcessor,
        PostProcessorConfig,
    )

    search_config = KnowledgeBaseInternalSearchConfig(limit=200, ...)
    post_config = PostProcessorConfig(max_tokens_for_sources=30_000, ...)

    search_service = KnowledgeBaseInternalSearchService.from_config(search_config)
    processor = InternalSearchPostProcessor.from_settings(settings, config=post_config)

    search_service.bind_settings(settings)
    search_service.state.search_queries = ["my query"]
    result = await search_service.run()

    chunks = await processor.process(
        result,
        query_text="my query",
        model_info=model_info,
    )
"""

from unique_toolkit.experimental.components.internal_search.base import (
    DEFAULT_LIMIT,
    InternalSearchBaseService,
    InternalSearchConfig,
    InternalSearchProgressMessage,
    InternalSearchResult,
    InternalSearchStage,
    InternalSearchState,
    SearchStringResult,
    TInternalSearchDeps,
)
from unique_toolkit.experimental.components.internal_search.chat import (
    ChatInternalSearchConfig,
    ChatInternalSearchDeps,
    ChatInternalSearchService,
)
from unique_toolkit.experimental.components.internal_search.knowledge_base import (
    UNSET,
    KnowledgeBaseInternalSearchConfig,
    KnowledgeBaseInternalSearchDeps,
    KnowledgeBaseInternalSearchService,
    KnowledgeBaseInternalSearchState,
)
from unique_toolkit.experimental.components.internal_search.post_processing import (
    InternalSearchPostProcessor,
    PostProcessorConfig,
)

__all__ = [
    # base
    "DEFAULT_LIMIT",
    "InternalSearchBaseService",
    "InternalSearchConfig",
    "InternalSearchProgressMessage",
    "InternalSearchResult",
    "InternalSearchStage",
    "InternalSearchState",
    "SearchStringResult",
    "TInternalSearchDeps",
    # chat
    "ChatInternalSearchConfig",
    "ChatInternalSearchDeps",
    "ChatInternalSearchService",
    # knowledge base
    "KnowledgeBaseInternalSearchConfig",
    "KnowledgeBaseInternalSearchDeps",
    "KnowledgeBaseInternalSearchService",
    "KnowledgeBaseInternalSearchState",
    "UNSET",
    # post-processing
    "InternalSearchPostProcessor",
    "PostProcessorConfig",
]
