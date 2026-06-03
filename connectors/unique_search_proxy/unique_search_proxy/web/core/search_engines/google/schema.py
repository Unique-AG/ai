from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from unique_search_proxy.web.core.schema import camelized_model_config
from unique_search_proxy.web.core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngineType,
)
from unique_search_proxy.web.core.search_engines.google.settings import (
    GoogleSearchSettings,
    get_google_search_settings,
)
from unique_search_proxy.web.core.search_engines.pagination import PageRequest
from unique_search_proxy.web.core.search_engines.params import (
    ParamExposure,
    llm_field_names,
    to_provider_params,
    validate_exposed_fields,
)


class GoogleEngineParameters(BaseModel):
    """All configurable Google Custom Search API parameters (single source of truth)."""

    model_config = camelized_model_config

    date_restrict: str | None = Field(
        default=None,
        description="Restricts results by date (e.g. d7, w2, m6)",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )
    exact_terms: str | None = Field(
        default=None,
        description="Phrase that all results must contain",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )
    exclude_terms: str | None = Field(
        default=None,
        description="Word or phrase that must not appear in results",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )
    file_type: str | None = Field(
        default=None,
        description="Restrict results to a file extension",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )
    gl: str | None = Field(
        default=None,
        description="Geolocation country code for the end user",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )
    hl: str | None = Field(
        default=None,
        description="Interface language",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )
    lr: str | None = Field(
        default=None,
        description="Restrict results to a language (e.g. lang_en)",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )
    safe: Literal["active", "off"] | None = Field(
        default="active",
        description="Safe-search level",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )
    site_search: str | None = Field(
        default=None,
        description="Site to always include or exclude from results",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )
    site_search_filter: Literal["e", "i"] | None = Field(
        default=None,
        description="Whether siteSearch is included (i) or excluded (e)",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )
    sort: str | None = Field(
        default=None,
        description="Sort expression (e.g. date)",
        json_schema_extra={"exposure": ParamExposure.EXPOSABLE.value},
    )

    def provider_query_params(self) -> dict[str, Any]:
        return to_provider_params(self)


class GoogleSearchCall(GoogleEngineParameters):
    """Per-invocation call surface (query is always LLM-visible)."""

    query: str = Field(
        ...,
        min_length=1,
        description="Search query string",
        json_schema_extra={"exposure": ParamExposure.ALWAYS_EXPOSED.value},
    )


class GoogleConfig(
    BaseSearchEngineConfig[SearchEngineType.GOOGLE], GoogleEngineParameters
):
    """Deployment config: engine id, fetch_size, parameter defaults, LLM exposure policy."""

    engine: Literal[SearchEngineType.GOOGLE] = SearchEngineType.GOOGLE

    search_engine_id: str | None = Field(
        default=None,
        description=(
            "Programmable Search Engine ID (cx). "
            "Overrides GOOGLE_SEARCH_ENGINE_ID when set."
        ),
        json_schema_extra={"exposure": ParamExposure.CONFIG_ONLY.value},
    )

    exposed_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Optional GoogleEngineParameters fields exposed to LLM callers. "
            "query is always exposed; fetchSize is config-only."
        ),
    )

    @field_validator("exposed_fields")
    @classmethod
    def _validate_exposed_fields(cls, value: list[str]) -> list[str]:
        return validate_exposed_fields(GoogleEngineParameters, value)

    def llm_field_names(self) -> list[str]:
        return llm_field_names(GoogleSearchCall, self.exposed_fields)

    def provider_query_params(self) -> dict[str, Any]:
        return GoogleEngineParameters.model_validate(
            self.model_dump(),
        ).provider_query_params()


@dataclass(frozen=True)
class GoogleCredentials:
    api_key: str
    search_engine_id: str
    api_endpoint: str

    @classmethod
    def from_settings(
        cls,
        settings: GoogleSearchSettings,
        *,
        search_engine_id: str | None = None,
    ) -> GoogleCredentials:
        assert settings.google_search_api_key is not None
        assert settings.google_search_api_endpoint is not None
        resolved_engine_id = search_engine_id or settings.google_search_engine_id
        assert resolved_engine_id is not None
        return cls(
            api_key=settings.google_search_api_key,
            search_engine_id=resolved_engine_id,
            api_endpoint=settings.google_search_api_endpoint,
        )

    @classmethod
    def from_env(cls, *, search_engine_id: str | None = None) -> GoogleCredentials:
        from unique_search_proxy.web.core.errors import EngineNotConfiguredError
        from unique_search_proxy.web.core.search_engines.base import SearchEngineType

        settings = get_google_search_settings()
        if (
            not settings.google_search_api_key
            or not settings.google_search_api_endpoint
        ):
            raise EngineNotConfiguredError(
                SearchEngineType.GOOGLE.value,
                kind="engine",
            )

        resolved_engine_id = search_engine_id or settings.google_search_engine_id
        if not resolved_engine_id:
            raise EngineNotConfiguredError(
                SearchEngineType.GOOGLE.value,
                kind="engine",
            )

        return cls.from_settings(
            settings,
            search_engine_id=resolved_engine_id,
        )


def build_google_query_params(
    *,
    query: str,
    credentials: GoogleCredentials,
    engine: GoogleEngineParameters,
    page: PageRequest,
) -> dict[str, Any]:
    """Assemble the Google API query string from public config + private runtime parts."""
    return {
        "q": query,
        "cx": credentials.search_engine_id,
        "key": credentials.api_key,
        "start": page.offset,
        "num": page.count,
        **engine.provider_query_params(),
    }
