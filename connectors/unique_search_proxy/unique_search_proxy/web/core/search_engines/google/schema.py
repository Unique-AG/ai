from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import DeactivatedNone

from unique_search_proxy.web.core.param_policy.exposable_param import ExposableParam
from unique_search_proxy.web.core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngineType,
)
from unique_search_proxy.web.core.search_engines.google.settings import (
    GoogleSearchSettings,
    default_google_search_engine_id,
    get_google_search_settings,
)
from unique_search_proxy.web.core.search_engines.pagination import PageRequest

GoogleSafeDefault: TypeAlias = Literal["active", "off"]
GoogleSiteSearchFilter: TypeAlias = Literal["e", "i"]

StrOrNone: TypeAlias = Annotated[str | None, DeactivatedNone]
SiteSearchFilterOrNone: TypeAlias = Annotated[
    GoogleSiteSearchFilter | None, DeactivatedNone
]

ExposableStrOrNone = ExposableParam[StrOrNone]
ExposableSiteSearchFilter = ExposableParam[SiteSearchFilterOrNone]


def _inactive_str_exposable() -> ExposableStrOrNone:
    return ExposableStrOrNone(expose=False, value=None)


def _inactive_site_search_filter_exposable() -> ExposableSiteSearchFilter:
    return ExposableSiteSearchFilter(expose=False, value=None)


class GoogleConfig(BaseSearchEngineConfig[Literal[SearchEngineType.GOOGLE]]):
    """Single source of truth for Google deployment + derived request/LLM surfaces."""

    engine: Literal[SearchEngineType.GOOGLE] = Field(
        default=SearchEngineType.GOOGLE,
        title="Search engine",
        description="Provider discriminator; must be `google` for this config.",
    )

    search_engine_id: StrOrNone = Field(
        default_factory=default_google_search_engine_id,
        title="Search engine ID (cx)",
        description=(
            "Google Programmable Search Engine ID (`cx`). "
            "Defaults from `GOOGLE_SEARCH_ENGINE_ID` when deployed. "
            "Not sent as a query parameter (resolved at runtime)."
        ),
    )

    safe: GoogleSafeDefault = Field(
        default="active",
        title="Safe search",
        description=(
            "SafeSearch level for every search: `active` (default) or `off`. "
            "Applied on all requests unless the call body overrides it."
        ),
    )

    gl: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        title="Geolocation (gl)",
        description=(
            "Two-letter ISO 3166-1 alpha-2 country code (Google `gl`). "
            "Set `value` for a fixed default; set `expose` so the LLM may override per query."
        ),
    )
    hl: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        title="Interface language (hl)",
        description=(
            "Language for snippets/UI (Google `hl`). "
            "`value` + `expose` behave like `gl`."
        ),
    )
    lr: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        title="Language restrict (lr)",
        description=(
            "Document language restrict (Google `lr`), e.g. `lang_en`. "
            "`value` + `expose` behave like `gl`."
        ),
    )
    date_restrict: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        alias="dateRestrict",
        title="Date restrict",
        description=(
            "Google `dateRestrict` recency filter (`d7`, `m1`, …). "
            "`value` + `expose` behave like `gl`."
        ),
    )
    exact_terms: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        alias="exactTerms",
        title="Exact terms",
        description=(
            "Phrase every hit must contain (Google `exactTerms`). "
            "`value` + `expose` behave like `gl`."
        ),
    )
    exclude_terms: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        alias="excludeTerms",
        title="Exclude terms",
        description=(
            "Phrase that must not appear (Google `excludeTerms`). "
            "`value` + `expose` behave like `gl`."
        ),
    )
    file_type: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        alias="fileType",
        title="File type",
        description=(
            "File extension filter (Google `fileType`), e.g. `pdf`. "
            "`value` + `expose` behave like `gl`."
        ),
    )
    site_search: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        alias="siteSearch",
        title="Site search",
        description=(
            "Site or domain (Google `siteSearch`). "
            "Pair with `siteSearchFilter`. `value` + `expose` behave like `gl`."
        ),
    )
    site_search_filter: ExposableSiteSearchFilter = Field(
        default_factory=_inactive_site_search_filter_exposable,
        alias="siteSearchFilter",
        title="Site search filter",
        description=(
            "With `siteSearch`: `i` = include only that site, `e` = exclude. "
            "`value` + `expose` behave like `gl`."
        ),
    )
    sort: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        title="Sort",
        description=(
            "Sort expression (Google `sort`), e.g. `date`. "
            "`value` + `expose` behave like `gl`."
        ),
    )


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
    request: BaseModel,
    page: PageRequest,
) -> dict[str, Any]:
    """Assemble the Google API query string from the derived request + credentials."""
    config = GoogleConfig()
    return {
        "q": query,
        "cx": credentials.search_engine_id,
        "key": credentials.api_key,
        "start": page.offset,
        "num": page.count,
        **config.provider_query_params_from(request),
    }


def google_request_model() -> type[BaseModel]:
    """Derived ``POST /v1/search`` model (cached via ``build_request_model``)."""
    from unique_search_proxy.web.core.projection import build_request_model

    return build_request_model(GoogleConfig)


GoogleSearchRequest = google_request_model()


__all__ = [
    "GoogleConfig",
    "GoogleCredentials",
    "GoogleSearchRequest",
    "build_google_query_params",
    "google_request_model",
]
