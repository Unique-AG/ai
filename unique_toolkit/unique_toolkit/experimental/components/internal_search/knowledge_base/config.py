from __future__ import annotations

import warnings
from typing import Annotated, Self

from pydantic import Field, model_validator

from unique_toolkit._common.config_checker import register_config
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
            "Not accepted for new configs. Use ``metadata_filter`` with "
            "``folderId`` / operator ``in`` and the raw scope ID values instead. "
            "If set, a deprecation warning is emitted and values are folded into "
            "a ``folderId in [scope_ids]`` metadata filter at search time."
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

    @model_validator(mode="after")
    def _warn_deprecated_scope_ids(self) -> Self:
        if self.scope_ids:
            warnings.warn(
                (
                    "KnowledgeBaseInternalSearchConfig.scope_ids is deprecated; "
                    "use metadata_filter with folderId operator 'in' instead."
                ),
                DeprecationWarning,
                stacklevel=5,  # Pydantic v2 model_validator adds ~3 frames above this validator
            )
        return self


__all__ = ["KnowledgeBaseInternalSearchConfig"]
