from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel, Field

from unique_search_proxy.web.core.schema import (
    ProviderConfigBase,
    SearchEngineRaw,
    WebSearchResults,
)

if TYPE_CHECKING:
    from httpx import AsyncClient

T = TypeVar("T", bound="SearchEngineType")


class SearchEngineMode(StrEnum):
    STANDARD = "standard"
    AGENT = "agent"


class SearchEngineType(StrEnum):
    """Registered search engine ids (JSON discriminator values)."""

    GOOGLE = "google"


_SEARCH_ENGINE_MODE_MAP: dict[SearchEngineType, SearchEngineMode] = {
    SearchEngineType.GOOGLE: SearchEngineMode.STANDARD,
}


def get_search_engine_mode(
    engine_type: SearchEngineType,
    *,
    override: SearchEngineMode | None = None,
) -> SearchEngineMode:
    if override is not None:
        return override
    return _SEARCH_ENGINE_MODE_MAP.get(engine_type, SearchEngineMode.STANDARD)


class BaseSearchEngineConfig(ProviderConfigBase, Generic[T]):
    """Shared search-engine config; each engine narrows ``engine`` with a Literal."""

    engine: T
    fetch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Configured result count for this deployment (not LLM-exposed)",
        json_schema_extra={"exposure": "config_only"},
    )


SearchEngineConfigT = TypeVar("SearchEngineConfigT", bound=BaseSearchEngineConfig)
SearchEngineCallT = TypeVar("SearchEngineCallT", bound=BaseModel)


class SearchEngine(ABC, Generic[SearchEngineConfigT, SearchEngineCallT]):
    """Search engine contract for v1 providers."""

    engine_id: str

    def __init__(
        self,
        config: SearchEngineConfigT,
        *,
        http_client: AsyncClient | None = None,
    ) -> None:
        self.config = config
        self._http_client = http_client

    @property
    @abstractmethod
    def snippet_only(self) -> bool:
        """When true, results need a crawler when includeContent is set."""

    @property
    @abstractmethod
    def mode(self) -> str:
        """Provider mode identifier for observability."""

    @abstractmethod
    async def search(
        self,
        call: SearchEngineCallT,
        *,
        timeout: int,
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        """Run search using a resolved per-engine call model."""
