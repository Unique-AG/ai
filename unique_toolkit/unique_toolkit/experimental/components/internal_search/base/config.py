from pydantic import BaseModel, Field

from unique_toolkit._common.config_checker import register_config
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.content.schemas import ContentSearchType

# 200 matches the tool's sort-enabled default — conservative by design.
# Callers who need higher recall (e.g. multi-query with post-processing) should set
# limit explicitly in config. The service does not cap by token budget; that is the
# post-processor's job via pick_content_chunks_for_token_window.
DEFAULT_LIMIT = 200


class InternalSearchSearchConfig(BaseModel):
    model_config = get_configuration_dict()

    search_type: ContentSearchType = Field(
        default=ContentSearchType.COMBINED,
        description="The type of search to perform. Two possible values: `COMBINED` or `VECTOR`.",
    )
    search_language: str = Field(
        default="english",
        description="The language to use for the search.",
    )
    max_search_strings: int = Field(
        default=10,
        ge=1,
        description="The maximum number of search strings to perform in a single tool call.",
    )


class InternalSearchFilterConfig(BaseModel):
    model_config = get_configuration_dict()

    score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score threshold to filter chunks on relevancy.",
    )
    limit: int = Field(
        default=DEFAULT_LIMIT,
        description=(
            "Maximum number of chunks to return per search query. "
            "Default is 200 — the conservative baseline. Increase for higher recall "
            "when a post-processor with token windowing follows."
        ),
    )


@register_config()
class InternalSearchConfig(BaseModel):
    """Retrieval-only config. Token budgeting, reranking and sorting live in PostProcessorConfig."""

    model_config = get_configuration_dict()

    search: InternalSearchSearchConfig = Field(
        default_factory=InternalSearchSearchConfig,
        description="Search-related configuration such as query mode, language, and multi-query settings.",
    )
    filtering: InternalSearchFilterConfig = Field(
        default_factory=InternalSearchFilterConfig,
        description="Result filtering configuration such as retrieval limit and score threshold.",
    )


__all__ = [
    "InternalSearchConfig",
    "DEFAULT_LIMIT",
    "InternalSearchFilterConfig",
    "InternalSearchSearchConfig",
]
