from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel, Field, model_validator

from unique_search_proxy_core.param_policy import QUERY_FIELD
from unique_search_proxy_core.param_policy.exposable_param import (
    merge_exposable_params_with_factory_defaults,
)
from unique_search_proxy_core.param_policy.resolver import ConfigRequestResolver
from unique_search_proxy_core.schema import (
    SearchEngineRaw,
    WebSearchResults,
    camelized_model_config,
)

if TYPE_CHECKING:
    from httpx import AsyncClient

T = TypeVar("T", bound="SearchEngineType")
SearchRequestT = TypeVar("SearchRequestT", bound=BaseModel)

ENGINE_FIELD = "engine"
FETCH_SIZE_FIELD = "fetch_size"
TIMEOUT_FIELD = "timeout"


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

    @classmethod
    def provider_param_exclude_fields(cls) -> set[str]:
        """Field names never forwarded to the upstream provider query string.

        The base set covers fields shared by every engine: the discriminator,
        request plumbing, and the query itself. Individual configs override this
        to drop provider-specific internal fields — e.g. Google adds
        ``search_engine_id`` (sent as the ``cx`` credential, not a query knob).
        """
        return {ENGINE_FIELD, FETCH_SIZE_FIELD, TIMEOUT_FIELD, QUERY_FIELD}

    @staticmethod
    def merge(
        config: BaseModel,
        overrides: dict[str, Any],
        *,
        query: str,
    ) -> BaseModel:
        """Merge deployment defaults + caller/LLM overrides + query into a request model."""
        request_model = ConfigRequestResolver.request_model(type(config))
        merged: dict[str, Any] = {
            **ConfigRequestResolver.resolve_values(
                config, exclude=frozenset({ENGINE_FIELD})
            ),
            **overrides,
            QUERY_FIELD: query,
        }
        engine = getattr(config, ENGINE_FIELD, None)
        if engine is not None and ENGINE_FIELD in request_model.model_fields:
            merged[ENGINE_FIELD] = getattr(engine, "value", engine)
        return request_model.model_validate(merged)

    @classmethod
    def provider_query_params(
        cls,
        request: BaseModel,
        *,
        by_alias: bool = True,
    ) -> dict[str, Any]:
        """Serialize forwardable provider knobs from a merged request model.

        Fields the config marks as non-forwardable (via
        :meth:`provider_param_exclude_fields`) are dropped so credentials and
        request plumbing never leak into the upstream query string.
        """
        return request.model_dump(
            mode="json",
            exclude_none=True,
            by_alias=by_alias,
            exclude=cls.provider_param_exclude_fields(),
        )


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
        """Run search using a flat request model (``GoogleSearchRequest``, …)."""
