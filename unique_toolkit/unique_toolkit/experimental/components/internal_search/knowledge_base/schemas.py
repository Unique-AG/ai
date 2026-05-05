from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from unique_toolkit.experimental.components.internal_search.base.schemas import (
    InternalSearchState,
)

if TYPE_CHECKING:
    from unique_toolkit import KnowledgeBaseService


class _UnsetType:
    """Sentinel — distinguishes 'not set' from None for metadata_filter_override."""

    def __repr__(self) -> str:
        return "UNSET"


UNSET: _UnsetType = _UnsetType()


@dataclass
class KnowledgeBaseInternalSearchDeps:
    knowledge_base_service: KnowledgeBaseService


@dataclass
class KnowledgeBaseInternalSearchState(InternalSearchState):
    metadata_filter_override: dict[str, Any] | None | _UnsetType = field(
        default_factory=lambda: UNSET
    )


__all__ = [
    "KnowledgeBaseInternalSearchState",
    "KnowledgeBaseInternalSearchDeps",
    "UNSET",
    "_UnsetType",
]
