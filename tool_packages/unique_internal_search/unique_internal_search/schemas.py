from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict
from unique_toolkit.chat.schemas import MessageLogStatus

if TYPE_CHECKING:
    from unique_toolkit._common.chunk_relevancy_sorter.service import (
        ChunkRelevancySorter,
    )
    from unique_toolkit.content.schemas import ContentChunk
    from unique_toolkit.language_model.infos import LanguageModelInfo
    from unique_toolkit.services.knowledge_base import KnowledgeBaseService


# ---------------------------------------------------------------------------
# Sentinel
# ---------------------------------------------------------------------------


class _UnsetType:
    """Sentinel for fields where None is a valid value and 'not set' is distinct."""

    _instance: _UnsetType | None = None

    def __new__(cls) -> _UnsetType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"


UNSET: _UnsetType = _UnsetType()


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


class SearchStage(StrEnum):
    RETRIEVING = "retrieving"
    RESORTING = "resorting"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"


class InternalSearchProgressMessage(BaseModel):
    """Progress event emitted by InternalSearchService during run().

    The Tool layer subscribes to these via the TypedEventBus to update
    message logs and progress reporters without the service knowing about
    chat tooling.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    stage: SearchStage
    status: MessageLogStatus
    search_queries: list[str]
    chunks: list[ContentChunk] | None = None  # only populated at COMPLETED stage


# ---------------------------------------------------------------------------
# Deps
# ---------------------------------------------------------------------------


@dataclass
class InternalSearchDeps:
    """Injected collaborators for InternalSearchService.

    A plain dataclass — holds live service instances that are not serializable.
    ``Deps`` TypeVar in ``BaseService`` is intentionally unbound, so no base class required.
    """

    knowledge_base_service: KnowledgeBaseService
    chunk_relevancy_sorter: ChunkRelevancySorter


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class InternalSearchState(BaseModel):
    """Per-invocation state set by the caller before each run().

    ``metadata_filter_override`` uses the UNSET sentinel to distinguish
    "caller did not set an override" from "caller explicitly wants no filter (None)".
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    search_queries: list[str]
    content_ids: list[str] | None = None
    chat_only: bool = False
    metadata_filter_override: dict[str, Any] | None | _UnsetType = UNSET
    language_model_info: LanguageModelInfo | None = None


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


class InternalSearchResult(BaseModel):
    """Return value of InternalSearchService.run()."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    chunks: list[ContentChunk]
    debug_info: dict[str, Any]
