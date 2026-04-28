from pydantic import BaseModel, Field

from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.config_checker import register_config
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit.agentic.tools.config import get_configuration_dict


@register_config()
class PostProcessorConfig(BaseModel):
    """Post-retrieval processing config: reranking, token windowing, output format.

    Intentionally separate from InternalSearchConfig — the search service is a
    pure retrieval primitive; everything here is the caller's post-processing pipeline.

    Server-side reranking (ContentRerankerConfig) belongs in the search config
    (KnowledgeBaseInternalSearchConfig / ChatInternalSearchConfig) because it is
    applied during the retrieval API call, not post-retrieval.
    """

    model_config = get_configuration_dict()

    chunk_relevancy_sort_config: ChunkRelevancySortConfig = Field(
        default_factory=ChunkRelevancySortConfig,
        description=(
            "Client-side chunk relevancy sort. When enabled, reranks each query's "
            "chunks against that query's text before interleaving."
        ),
    )
    max_tokens_for_sources: int = Field(
        default=30_000,
        description="Hard token-budget cap for the returned chunks.",
        json_schema_extra=RJSFMetaTag.SpecialWidget.hidden(),
    )
    percentage_of_input_tokens_for_sources: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction of the model's max input tokens to use for sources. "
            "Used when model_info is provided to process(); otherwise falls back to max_tokens_for_sources."
        ),
    )
    chunked_sources: bool = Field(
        default=True,
        description="If True, each chunk is a separate source. If False, chunks from the same document are merged.",
    )
    metadata_chunk_sections: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Metadata sections appended to each chunk's text as the final processing step. "
            "Keys are metadata field names; values are template strings with {} as placeholder. "
            "Example: {'source': '<|source|>{}<|/source|>'}."
        ),
    )


__all__ = ["PostProcessorConfig"]
