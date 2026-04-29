from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field
from typing_extensions import TypeVar

from unique_toolkit.chat.schemas import MessageLogStatus
from unique_toolkit.content.schemas import ContentChunk


class SearchStringResult(BaseModel):
    query: str
    chunks: list[ContentChunk]


class InternalSearchStage(StrEnum):
    RETRIEVING = "retrieving"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"


class InternalSearchProgressMessage(BaseModel):
    stage: InternalSearchStage
    status: MessageLogStatus
    search_queries: list[str]
    chunks: list[ContentChunk] | None = None


TInternalSearchDeps = TypeVar("TInternalSearchDeps")


@dataclass
class InternalSearchState:
    search_queries: list[str]
    content_ids: list[str] | None = None


class InternalSearchResult(BaseModel):
    chunks: list[ContentChunk]
    """Interleaved flat chunk list — for callers that skip the post-processor."""
    debug_info: dict[str, Any]
    search_string_results: list[SearchStringResult] = Field(default_factory=list)
    """Per-query results before interleaving — for the post-processor's per-query rerank."""


__all__ = [
    "InternalSearchProgressMessage",
    "InternalSearchResult",
    "InternalSearchStage",
    "InternalSearchState",
    "SearchStringResult",
    "TInternalSearchDeps",
]
