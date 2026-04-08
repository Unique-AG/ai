from pydantic import Field

from unique_toolkit.components.internal_search.base.config import (
    InternalSearchConfig,
)


class KnowledgeBaseInternalSearchConfig(InternalSearchConfig):
    metadata_filter: dict | None = Field(
        default=None,
        description="Static metadata filter applied to every KB search. "
        "Overridden by chat context filter or per-invocation state override.",
    )


__all__ = ["KnowledgeBaseInternalSearchConfig"]
