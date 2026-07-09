from __future__ import annotations

from typing import Annotated, ClassVar, Literal, TypeAlias

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.schema import DeactivatedNone
from unique_search_proxy_core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngineType,
)

GoogleSafeDefault: TypeAlias = Literal["active", "off"]
GoogleSiteSearchFilter: TypeAlias = Literal["e", "i"]

#: Config field carrying the Programmable Search Engine ID (``cx``); sent as a
#: credential, never as a query-string knob.
SEARCH_ENGINE_ID_FIELD = "search_engine_id"

StrOrNone: TypeAlias = Annotated[str, Field(title="String")] | DeactivatedNone
SiteSearchFilterOrNone: TypeAlias = (
    Annotated[GoogleSiteSearchFilter, Field(title="Site Search Filter")]
    | DeactivatedNone
)

ExposableStrOrNone = ExposableParam[StrOrNone]
ExposableSiteSearchFilter = ExposableParam[SiteSearchFilterOrNone]


def _inactive_str_exposable() -> ExposableStrOrNone:
    return ExposableStrOrNone(expose=False, value=None)


def _inactive_site_search_filter_exposable() -> ExposableSiteSearchFilter:
    return ExposableSiteSearchFilter(expose=False, value=None)


class GoogleConfig(BaseSearchEngineConfig[Literal[SearchEngineType.GOOGLE]]):
    """Single source of truth for Google deployment + derived request/LLM surfaces."""

    _request_model_name: ClassVar[str] = "GoogleSearchRequest"
    _exposed_params_model_name: ClassVar[str] = "GoogleExposedParams"

    # `search_engine_id` is the Programmable Search Engine credential (`cx`),
    # resolved server-side — never forwarded as a provider query knob.
    _provider_param_exclude_fields: ClassVar[frozenset[str]] = (
        BaseSearchEngineConfig._provider_param_exclude_fields | {SEARCH_ENGINE_ID_FIELD}
    )

    engine: Annotated[
        Literal[SearchEngineType.GOOGLE], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
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
        default=_inactive_str_exposable(),
        title="Geolocation (gl)",
        description="Two-letter ISO 3166-1 alpha-2 country code (Google `gl`).",
    )
    hl: ExposableStrOrNone = Field(
        default=_inactive_str_exposable(),
        title="Interface language (hl)",
        description="Language for snippets and UI (Google `hl`).",
    )
    lr: ExposableStrOrNone = Field(
        default=_inactive_str_exposable(),
        title="Language restrict (lr)",
        description="Document language restrict (Google `lr`), e.g. `lang_en`.",
    )
    date_restrict: ExposableStrOrNone = Field(
        default=_inactive_str_exposable(),
        alias="dateRestrict",
        title="Date restrict",
        description="Recency filter (Google `dateRestrict`), e.g. `d7`, `m1`.",
    )
    exact_terms: ExposableStrOrNone = Field(
        default=_inactive_str_exposable(),
        alias="exactTerms",
        title="Exact terms",
        description="Phrase every hit must contain (Google `exactTerms`).",
    )
    exclude_terms: ExposableStrOrNone = Field(
        default=_inactive_str_exposable(),
        alias="excludeTerms",
        title="Exclude terms",
        description="Phrase that must not appear in results (Google `excludeTerms`).",
    )
    file_type: ExposableStrOrNone = Field(
        default=_inactive_str_exposable(),
        alias="fileType",
        title="File type",
        description="File extension filter (Google `fileType`), e.g. `pdf`.",
    )
    site_search: ExposableStrOrNone = Field(
        default=_inactive_str_exposable(),
        alias="siteSearch",
        title="Site search",
        description="Site or domain to restrict results to (Google `siteSearch`).",
    )
    site_search_filter: ExposableSiteSearchFilter = Field(
        default=_inactive_site_search_filter_exposable(),
        alias="siteSearchFilter",
        title="Site search filter",
        description=(
            "With `siteSearch`: `i` = include only that site, `e` = exclude it "
            "(Google `siteSearchFilter`)."
        ),
    )
    sort: ExposableStrOrNone = Field(
        default=_inactive_str_exposable(),
        title="Sort",
        description="Sort expression (Google `sort`), e.g. `date`.",
    )


GoogleSearchRequest = GoogleConfig.request_model()


__all__ = [
    "GoogleConfig",
    "GoogleSearchRequest",
    "SEARCH_ENGINE_ID_FIELD",
]
