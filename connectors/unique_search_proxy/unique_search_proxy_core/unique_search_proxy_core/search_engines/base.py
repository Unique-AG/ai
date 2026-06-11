from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

from unique_search_proxy_core.param_policy.exposable_param import (
    merge_exposable_params_with_factory_defaults,
)
from unique_search_proxy_core.schema import (
    SearchEngineRaw,
    WebSearchResults,
    camelized_model_config,
)

if TYPE_CHECKING:
    from httpx import AsyncClient

T = TypeVar("T", bound="SearchEngineType")
SearchRequestT = TypeVar("SearchRequestT", bound=BaseModel)


class SearchEngineMode(StrEnum):
    STANDARD = "standard"
    AGENT = "agent"


class SearchEngineType(StrEnum):
    """Registered search engine ids (JSON discriminator values)."""

    GOOGLE = "google"
    BRAVE = "brave"
    PERPLEXITY = "perplexity"


_SEARCH_ENGINE_MODE_MAP: dict[SearchEngineType, SearchEngineMode] = {
    SearchEngineType.GOOGLE: SearchEngineMode.STANDARD,
    SearchEngineType.BRAVE: SearchEngineMode.STANDARD,
    SearchEngineType.PERPLEXITY: SearchEngineMode.STANDARD,
}


def get_search_engine_mode(
    engine_type: SearchEngineType,
    *,
    override: SearchEngineMode | None = None,
) -> SearchEngineMode:
    if override is not None:
        return override
    return _SEARCH_ENGINE_MODE_MAP.get(engine_type, SearchEngineMode.STANDARD)


class BaseSearchEngineConfig(BaseModel, Generic[T]):
    model_config = camelized_model_config
    """Shared search-engine config; each engine narrows ``engine`` with a Literal."""

    engine: T
    fetch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Default result count merged into each search request",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="Request timeout in seconds",
    )

    @model_validator(mode="before")
    @classmethod
    def _merge_exposable_factory_defaults(cls, data: Any) -> Any:
        """Merge exposable knobs with field ``default_factory`` when JSON omits ``value``."""
        return merge_exposable_params_with_factory_defaults(cls, data)

    def provider_query_params_from(self, request: BaseModel, by_alias: bool = True) -> dict[str, Any]:
        """Provider query string params from a derived ``*ConfigRequest`` model."""
        from unique_search_proxy_core.search_engines.params import (
            provider_query_params_from_request,
        )

        return provider_query_params_from_request(request, type(self), by_alias=by_alias)


class SearchEngine(ABC, Generic[SearchRequestT]):
    """Search engine contract for v1 providers."""

    engine_id: str

    def __init__(
        self,
        *,
        http_client: AsyncClient | None = None,
    ) -> None:
        self._http_client = http_client

    @property
    @abstractmethod
    def mode(self) -> str:
        """Provider mode identifier for observability."""

    @abstractmethod
    async def search(
        self,
        request: SearchRequestT,
    ) -> tuple[SearchEngineRaw, WebSearchResults]:
        """Run search using a flat request model (``GoogleRequest``, …)."""
