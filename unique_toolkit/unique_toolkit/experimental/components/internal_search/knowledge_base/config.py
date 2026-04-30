from typing import Annotated, cast

from pydantic import Field, model_validator

from unique_toolkit._common.config_checker import register_config
from unique_toolkit._common.metadata_filter_scope import (
    fold_deprecated_scope_ids_in_config_data,
)
from unique_toolkit._common.pydantic_helpers import DeactivatedNone
from unique_toolkit.content.schemas import ContentRerankerConfig
from unique_toolkit.experimental.components.internal_search.base.config import (
    InternalSearchConfig,
)


@register_config()
class KnowledgeBaseInternalSearchConfig(InternalSearchConfig):
    scope_ids: list[str] | DeactivatedNone = Field(
        default=None,
        title="Active",
        deprecated=True,
        description=(
            "Deprecated. Use ``metadata_filter`` with a ``folderId`` ``in`` clause instead. "
            "When set, values are merged into ``metadata_filter`` at validation time."
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

    @model_validator(mode="before")
    @classmethod
    def _fold_scope_ids_into_metadata_filter(cls, data: object) -> object:
        if isinstance(data, dict):
            return fold_deprecated_scope_ids_in_config_data(
                cast("dict[str, object]", data)
            )
        return data


__all__ = ["KnowledgeBaseInternalSearchConfig"]
