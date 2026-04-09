from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from unique_toolkit.components.internal_search.base.schemas import InternalSearchState

if TYPE_CHECKING:
    from unique_toolkit import KnowledgeBaseService
    from unique_toolkit._common.chunk_relevancy_sorter.service import (
        ChunkRelevancySorter,
    )


class _UnsetType:
    """Singleton sentinel — distinguishes 'not set' from None for metadata_filter_override."""

    _instance: _UnsetType | None = None

    def __new__(cls) -> _UnsetType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"


UNSET: _UnsetType = _UnsetType()


@dataclass
class KnowledgeBaseInternalSearchDeps:
    chunk_relevancy_sorter: ChunkRelevancySorter
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
]
