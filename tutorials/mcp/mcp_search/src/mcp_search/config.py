"""Tool-level configuration for the Knowledge Base Search MCP tool.

``SearchToolConfig`` is the single RJSF config model for the search tool.
It holds one ``service_config`` key (``KnowledgeBaseInternalSearchConfig``)
which is passed directly to :class:`KnowledgeBaseInternalSearchService` via
``from_config()``, with no field mapping required.

Admin sets ``service_config`` fields at deployment time to control the search
backend (metadata filter, limit, reranker, etc.).
``post_processing`` controls post-retrieval behaviour (token budget, reranking).
"""

from pydantic import BaseModel, Field

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.experimental.components.internal_search import (
    KnowledgeBaseInternalSearchConfig,
    PostProcessorConfig,
)


class SearchToolConfig(BaseModel):
    model_config = get_configuration_dict()

    service_config: KnowledgeBaseInternalSearchConfig = Field(
        default_factory=lambda: KnowledgeBaseInternalSearchConfig(
            metadata_filter={
                "path": ["folderId"],
                "operator": "isNotNull",
                "value": None,
            }
        )
    )
    post_processing: PostProcessorConfig = Field(default_factory=PostProcessorConfig)
