from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Mapping, TypeVar

from pydantic import BaseModel, Field, model_validator

from unique_search_proxy_core.param_policy import QUERY_FIELD
from unique_search_proxy_core.param_policy.derive import (
    derive_exposed_params_model,
    derive_request_model,
)
from unique_search_proxy_core.param_policy.exposable_param import (
    ExposableParam,
    merge_exposable_params_with_factory_defaults,
)
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.param_policy.request_base import SearchRequestBase
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
    """Shared search-engine config; each engine narrows ``engine`` with a Literal.

    The config class owns its entire parameter lifecycle:

    - :meth:`request_model` — the HTTP request body model.
    - :meth:`exposed_params_model` — the LLM-facing knobs of this deployment.
    - :meth:`merge` — deployment defaults + LLM overrides -> validated request.
    - :meth:`provider_query_params` — request -> upstream provider dict.
    """

    model_config = camelized_model_config

    #: Fields never forwarded to the upstream provider query string: the
    #: discriminator, request plumbing, and the query itself. Engine configs
    #: extend this to drop provider-internal fields — e.g. Google adds
    #: ``search_engine_id`` (sent as the ``cx`` credential, not a query knob).
    _provider_param_exclude_fields: ClassVar[frozenset[str]] = frozenset(
        {ENGINE_FIELD, FETCH_SIZE_FIELD, TIMEOUT_FIELD, QUERY_FIELD},
    )

    #: Names of the derived models; set by every concrete engine config.
    _request_model_name: ClassVar[str]
    _exposed_params_model_name: ClassVar[str]

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
    def request_model(cls) -> type[BaseModel]:
        """HTTP request body model, cached per config class.

        :class:`SearchRequestBase` (required ``query``) + this config's fields,
        with ``ExposableParam`` knobs unwrapped to optional plain types.

        Example: ``GoogleConfig.request_model()`` -> ``GoogleSearchRequest``.
        """
        return derive_request_model(
            cls,
            base=SearchRequestBase,
            name=cls._request_model_name,
        )

    def exposed_params_model(self) -> type[ExposedParams] | None:
        """Plain model class with exactly the knobs this deployment exposed.

        One optional field per config field whose ``ExposableParam`` has
        ``expose=True``: camelCase alias, description-only schema, no admin
        defaults. Returns ``None`` when nothing is exposed. Consumers subclass
        the result (or pass it as an extra base to ``create_model``) to graft
        the knobs onto their own tool-parameter models.

        Example: ``config.exposed_params_model()`` -> ``GoogleExposedParams``.
        """
        return derive_exposed_params_model(
            self,
            name=type(self)._exposed_params_model_name,
        )

    def merge(self, overrides: Mapping[str, Any], *, query: str) -> BaseModel:
        """Deployment defaults + LLM/caller overrides + query -> validated request.

        Defaults: plain fields contribute their value; ``ExposableParam`` knobs
        contribute ``value`` when not ``None`` (deactivated knobs are dropped);
        ``engine`` always comes from this config. ``overrides`` win over
        defaults. Validates into :meth:`request_model`.

        Example: ``config.merge({"date_restrict": "d7"}, query="ai news")``.
        """
        merged: dict[str, Any] = self._merge_defaults()
        merged.update(overrides)
        merged[QUERY_FIELD] = query
        merged[ENGINE_FIELD] = self.engine
        return type(self).request_model().model_validate(merged)

    def _merge_defaults(self) -> dict[str, Any]:
        """Plain deployment default values (``ExposableParam`` resolved, ``None`` dropped)."""
        defaults: dict[str, Any] = {}
        for field_name in type(self).model_fields:
            if field_name == ENGINE_FIELD:
                continue
            raw = getattr(self, field_name)
            if isinstance(raw, ExposableParam):
                if raw.value is not None:
                    defaults[field_name] = raw.value
            elif raw is not None:
                defaults[field_name] = raw
        return defaults

    @classmethod
    def provider_query_params(
        cls,
        request: BaseModel,
        *,
        by_alias: bool = True,
    ) -> dict[str, Any]:
        """Serialize a merged request for the upstream provider.

        Drops ``None`` values and the fields in
        :attr:`_provider_param_exclude_fields`, so credentials and request
        plumbing never leak into the upstream query string.

        Example: ``GoogleConfig.provider_query_params(request)``.
        """
        return request.model_dump(
            mode="json",
            exclude_none=True,
            by_alias=by_alias,
            exclude=set(cls._provider_param_exclude_fields),
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
