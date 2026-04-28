from typing import Annotated

from pydantic import Field

from unique_toolkit._common.config_checker import register_config
from unique_toolkit._common.pydantic_helpers import DeactivatedNone
from unique_toolkit.content.schemas import ContentRerankerConfig
from unique_toolkit.experimental.components.internal_search.base.config import (
    InternalSearchConfig,
)


@register_config()
class KnowledgeBaseInternalSearchConfig(InternalSearchConfig):
    scope_ids: Annotated[list[str], Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description=(
            "Knowledge-base scope IDs to restrict the search to. "
            "When set, takes precedence over metadata_filter — the two are "
            "mutually exclusive at the API level (scope_ids OR metadata_filter)."
        ),
    )
    metadata_filter: dict[str, object] | None = Field(
        default=None,
        description=(
            "Static metadata filter applied to every KB search. "
            "Overridden by chat context filter or per-invocation state override."
        ),
    )
    reranker_config: (
        Annotated[ContentRerankerConfig, Field(title="Active")] | DeactivatedNone
    ) = Field(
        default=None,
        description=(
            "Server-side reranker applied during retrieval. "
            "Passed directly to the KB search API — distinct from the "
            "client-side chunk_relevancy_sort_config in PostProcessorConfig."
        ),
    )


__all__ = ["KnowledgeBaseInternalSearchConfig"]
