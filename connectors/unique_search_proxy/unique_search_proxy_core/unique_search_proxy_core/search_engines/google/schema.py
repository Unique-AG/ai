from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, Field

from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.projection import build_request_model
from unique_search_proxy_core.schema import DeactivatedNone
from unique_search_proxy_core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngineType,
)

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
        default=None,
        title="Search engine ID (cx)",
        description=(
            "Google Programmable Search Engine ID (`cx`). "
            "Resolved from deployment env at runtime when not set. "
            "Not sent as a query parameter."
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


def google_request_model() -> type[BaseModel]:
    """Derived ``POST /v1/search`` model (cached via ``build_request_model``)."""
    return build_request_model(GoogleConfig)


GoogleRequest = google_request_model()


__all__ = [
    "GoogleConfig",
    "GoogleRequest",
    "google_request_model",
]
