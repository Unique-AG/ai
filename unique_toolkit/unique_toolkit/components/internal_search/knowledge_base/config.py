from typing import Annotated

from pydantic import Field

from unique_toolkit._common.config_checker import register_config
from unique_toolkit._common.pydantic_helpers import DeactivatedNone
from unique_toolkit.components.internal_search.base.config import (
    InternalSearchConfig,
)


@register_config()
class KnowledgeBaseInternalSearchConfig(InternalSearchConfig):
    scope_ids: Annotated[list[str], Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="The scope ids to use for the search.",
    )
    metadata_filter: dict[str, object] | None = Field(
        default=None,
        description=(
            "Static metadata filter applied to every KB search. "
            "Overridden by chat context filter or per-invocation state override."
        ),
    )


__all__ = ["KnowledgeBaseInternalSearchConfig"]
