from pydantic import Field

from unique_toolkit._common.config_checker import register_config
from unique_toolkit.components.internal_search.base.config import (
    InternalSearchConfig,
)


@register_config()
class KnowledgeBaseInternalSearchConfig(InternalSearchConfig):
    metadata_filter: dict | None = Field(
        default=None,
        description="Static metadata filter applied to every KB search. "
        "Overridden by chat context filter or per-invocation state override.",
    )


__all__ = ["KnowledgeBaseInternalSearchConfig"]
