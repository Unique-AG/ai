from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
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
    debug_info: dict[str, Any]


__all__ = [
    "InternalSearchProgressMessage",
    "InternalSearchResult",
    "InternalSearchStage",
    "InternalSearchState",
    "SearchStringResult",
    "TInternalSearchDeps",
]
