from typing import Annotated

from pydantic import BaseModel, Field

from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.config_checker import register_config
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import DeactivatedNone
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.content.schemas import ContentRerankerConfig


@register_config()
class PostProcessorConfig(BaseModel):
    """Post-retrieval processing config: reranking, token windowing, and output format.

    Intentionally separate from InternalSearchConfig — the search service is a
    pure retrieval primitive; everything here is the caller's post-processing pipeline.
    """

    model_config = get_configuration_dict()

    reranker_config: (
        Annotated[ContentRerankerConfig, Field(title="Active")] | DeactivatedNone
    ) = Field(
        default=None,
        description="Reranker to apply after retrieval. When set, re-scores chunks against the query.",
    )
    chunk_relevancy_sort_config: ChunkRelevancySortConfig = Field(
        default_factory=ChunkRelevancySortConfig,
        description="Chunk relevancy sort config. When enabled, re-orders chunks by relevancy score.",
    )
    max_tokens_for_sources: Annotated[int, RJSFMetaTag.SpecialWidget.hidden()] = Field(
        default=30_000,
        description="Hard token-budget cap for the returned chunks.",
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


__all__ = ["PostProcessorConfig"]
