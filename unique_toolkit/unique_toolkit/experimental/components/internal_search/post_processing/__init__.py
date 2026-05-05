"""Post-retrieval processing for internal search results.

!!! warning "Experimental"
    This subpackage lives under :mod:`unique_toolkit.experimental` and its
    API may change between minor releases.

Applies reranking, token-budget windowing, and chunk sorting/merging to the
raw chunks returned by :class:`~unique_toolkit.experimental.components.internal_search.base.service.InternalSearchBaseService`.
The search service is a pure retrieval primitive; this module owns the
post-processing pipeline so callers can compose only the steps they need.

Typical usage::

    from unique_toolkit.experimental.components.internal_search import (
        KBInternalSearchService,
        KBInternalSearchConfig,
        InternalSearchPostProcessor,
        PostProcessorConfig,
    )

    search_service = KBInternalSearchService.from_config(search_config)
    processor = InternalSearchPostProcessor.from_settings(settings, config=post_config)

    search_service.bind_settings(settings)
    search_service.state.search_queries = ["quarterly earnings"]
    result = await search_service.run()

    chunks = await processor.process(
        result,
        query_text="quarterly earnings",
        model_info=model_info,
    )

Modules:

- :mod:`unique_toolkit.experimental.components.internal_search.post_processing.config` —
  :class:`PostProcessorConfig`: reranker, token window, and output format settings.
- :mod:`unique_toolkit.experimental.components.internal_search.post_processing.service` —
  :class:`InternalSearchPostProcessor`: the processing service.
"""

from unique_toolkit.experimental.components.internal_search.post_processing.config import (
    PostProcessorConfig,
)
from unique_toolkit.experimental.components.internal_search.post_processing.service import (
    InternalSearchPostProcessor,
)

__all__ = [
    "InternalSearchPostProcessor",
    "PostProcessorConfig",
]
