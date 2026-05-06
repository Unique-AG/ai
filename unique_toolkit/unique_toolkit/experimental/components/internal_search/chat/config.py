from typing import Annotated

from pydantic import Field

from unique_toolkit._common.config_checker import register_config
from unique_toolkit._common.pydantic_helpers import DeactivatedNone
from unique_toolkit.content.schemas import ContentRerankerConfig
from unique_toolkit.experimental.components.internal_search.base.config import (
    InternalSearchConfig,
)


@register_config()
class ChatInternalSearchConfig(InternalSearchConfig):
    reranker_config: (
        Annotated[ContentRerankerConfig, Field(title="Active")] | DeactivatedNone
    ) = Field(
        default=None,
        description=(
            "Server-side reranker applied during retrieval. "
            "Passed directly to the chat search API — distinct from the "
            "client-side chunk_relevancy_sort_config in PostProcessorConfig."
        ),
    )


__all__ = ["ChatInternalSearchConfig"]
