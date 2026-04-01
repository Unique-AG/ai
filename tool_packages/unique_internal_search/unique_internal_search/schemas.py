from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit.chat.schemas import MessageLogStatus
from unique_toolkit.content.schemas import (
    ContentChunk,
    ContentRerankerConfig,
    ContentSearchType,
)

if TYPE_CHECKING:
    from unique_toolkit._common.chunk_relevancy_sorter.service import (
        ChunkRelevancySorter,
    )
    from unique_toolkit.language_model.infos import LanguageModelInfo

DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_ENABLED = 200
DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_DISABLED = 1000


class InternalSearchServiceConfig(BaseModel):
    """Lean service config — search execution only, no tool UI or RJSF annotations.

    config.py's InternalSearchConfig inherits from this and adds tool UI fields.
    """

    search_type: ContentSearchType = ContentSearchType.COMBINED
    limit: int = DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_DISABLED
    max_search_strings: int = Field(default=10, ge=1)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    scope_ids: list[str] | None = None
    search_language: str = "english"
    reranker_config: ContentRerankerConfig | None = None
    chunked_sources: bool = True
    chat_only: bool = False
    scope_to_chat_on_upload: bool = False
    exclude_uploaded_files: bool = False
    enable_multiple_search_strings_execution: bool = True
    chunk_relevancy_sort_config: ChunkRelevancySortConfig = Field(
        default_factory=ChunkRelevancySortConfig
    )
    max_tokens_for_sources: int = 30_000
    percentage_of_input_tokens_for_sources: float = Field(default=0.4, ge=0.0, le=1.0)


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


class SearchStage(StrEnum):
    RETRIEVING = "retrieving"
    RESORTING = "resorting"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"


class InternalSearchProgressMessage(BaseModel):
    """Published by the service during run(). Tool layer subscribes to handle UI updates."""

    stage: SearchStage
    status: MessageLogStatus
    search_queries: list[str]
    chunks: list[ContentChunk] | None = None  # only populated at COMPLETED stage


@dataclass
class InternalSearchDeps:
    chunk_relevancy_sorter: ChunkRelevancySorter


@dataclass
class InternalSearchState:
    """Per-invocation state, set by the caller before each run().

    metadata_filter_override uses UNSET to distinguish 'not set' (fall back to
    context.chat.metadata_filter) from None (explicitly no filter).
    """

    search_queries: list[str]
    content_ids: list[str] | None = None
    chat_only: bool = False
    metadata_filter_override: dict[str, Any] | None | _UnsetType = field(
        default_factory=lambda: UNSET
    )
    language_model_info: LanguageModelInfo | None = None
    language_model_max_input_tokens: int | None = None

    # get_max_tokens needs to be in state since it depends on used language_model_info, which are per req;
    # percentages etc come from the config
    def get_max_tokens(self, *, percentage: float, fallback: int) -> int:
        if self.language_model_max_input_tokens is not None:
            return int(self.language_model_max_input_tokens * percentage)
        return fallback


class InternalSearchResult(BaseModel):
    chunks: list[ContentChunk]
    debug_info: dict[str, Any]
