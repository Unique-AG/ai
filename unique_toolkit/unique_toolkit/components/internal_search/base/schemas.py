from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from typing_extensions import Protocol, TypeVar

from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit.chat.schemas import MessageLogStatus
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelInfo


class SearchStringResult(BaseModel):
    query: str
    chunks: list[ContentChunk]


class InternalSearchStage(StrEnum):
    RETRIEVING = "retrieving"
    RESORTING = "resorting"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"


class InternalSearchProgressMessage(BaseModel):
    stage: InternalSearchStage
    status: MessageLogStatus
    search_queries: list[str]
    chunks: list[ContentChunk] | None = None


class HasChunkRelevancySorter(Protocol):
    chunk_relevancy_sorter: ChunkRelevancySorter


TInternalSearchDeps = TypeVar("TInternalSearchDeps", bound=HasChunkRelevancySorter)


@dataclass
class InternalSearchState:
    search_queries: list[str]
    language_model_info: LanguageModelInfo | None = None
    language_model_max_input_tokens: int | None = None

    def get_max_tokens(self, *, percentage: float, fallback: int) -> int:
        if self.language_model_max_input_tokens is not None:
            return int(self.language_model_max_input_tokens * percentage)
        return fallback


class InternalSearchResult(BaseModel):
    chunks: list[ContentChunk]
    debug_info: dict[str, Any]


__all__ = [
    "InternalSearchProgressMessage",
    "InternalSearchResult",
    "InternalSearchStage",
    "InternalSearchState",
    "SearchStringResult",
    "TInternalSearchDeps",
]
