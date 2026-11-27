from __future__ import annotations

from typing import Annotated, ClassVar, Literal, TypeAlias

from pydantic import Field, WithJsonSchema
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.pydantic_helpers import NoneToDefault

from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.schema import DeactivatedNone
from unique_search_proxy_core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngineType,
)

# Firecrawl's own ceiling for ``limit``.
FIRECRAWL_MAX_RESULTS = 100
FIRECRAWL_MAX_QUERY_LENGTH = 500

FirecrawlSearchSource: TypeAlias = Literal["web", "news"]
FirecrawlSourceChoice: TypeAlias = Literal["web", "news", "web_and_news"]
FirecrawlCategory: TypeAlias = Literal["research", "pdf", "gov", "developer"]
# ``deployment`` adds nothing to what the Search Proxy is deployed with.
FirecrawlSearchZeroDataRetention: TypeAlias = Literal["deployment", "anon", "zdr"]

FIRECRAWL_SOURCES: dict[FirecrawlSourceChoice, list[FirecrawlSearchSource]] = {
    "web": ["web"],
    "news": ["news"],
    "web_and_news": ["web", "news"],
}
FirecrawlTimeFilter: TypeAlias = Literal["qdr:h", "qdr:d", "qdr:w", "qdr:m", "qdr:y"]

_TIME_FILTER_LABELS: dict[FirecrawlTimeFilter, str] = {
    "qdr:h": "Past hour",
    "qdr:d": "Past day",
    "qdr:w": "Past week",
    "qdr:m": "Past month",
    "qdr:y": "Past year",
}

# The UI schema generator drops tags on ``ExposableParam`` values, so labels
# come from ``oneOf`` titles instead of ``ui:enumNames``.
TimeFilterOrNone: TypeAlias = (
    Annotated[
        FirecrawlTimeFilter,
        WithJsonSchema(
            {
                "type": "string",
                "title": "Recent results only",
                "oneOf": [
                    {"const": code, "title": label}
                    for code, label in _TIME_FILTER_LABELS.items()
                ],
            }
        ),
    ]
    | Annotated[None, Field(title="No filter", description="None")]
)
CountryOrNone: TypeAlias = (
    Annotated[str, Field(title="Country code", pattern=r"^[A-Z]{2}$")]
    | Annotated[None, Field(title="Firecrawl default (US)", description="None")]
)
LocationOrNone: TypeAlias = (
    Annotated[str, Field(title="Location", min_length=1)] | DeactivatedNone
)
DomainListOrNone: TypeAlias = (
    Annotated[list[str], Field(title="Domains", max_length=100)] | DeactivatedNone
)
_CATEGORY_LABELS: dict[FirecrawlCategory, str] = {
    "research": "Academic and research sites",
    "pdf": "PDF documents",
    "gov": "Government publications",
    "developer": "Developer sites",
}
CategoryOrNone: TypeAlias = (
    Annotated[
        FirecrawlCategory,
        WithJsonSchema(
            {
                "type": "string",
                "title": "One category only",
                "oneOf": [
                    {"const": code, "title": label}
                    for code, label in _CATEGORY_LABELS.items()
                ],
            }
        ),
    ]
    | Annotated[None, Field(title="All results", description="None")]
)

ExposableTimeFilter = ExposableParam[TimeFilterOrNone]
ExposableCountry = ExposableParam[CountryOrNone]
ExposableLocation = ExposableParam[LocationOrNone]
ExposableDomainList = ExposableParam[DomainListOrNone]
ExposableCategory = ExposableParam[CategoryOrNone]


class FirecrawlSearchConfig(
    BaseSearchEngineConfig[Literal[SearchEngineType.FIRECRAWL]]
):
    """Firecrawl ``POST /v2/search`` deployment config: titles and previews."""

    _request_model_name: ClassVar[str] = "FirecrawlSearchRequest"
    _exposed_params_model_name: ClassVar[str] = "FirecrawlExposedParams"

    engine: Annotated[
        Literal[SearchEngineType.FIRECRAWL], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=SearchEngineType.FIRECRAWL,
        title="Search engine",
        description="Provider discriminator; must be `firecrawl` for this config.",
    )
    fetch_size: int = Field(
        default=10,
        ge=1,
        le=FIRECRAWL_MAX_RESULTS,
        description=(
            "Number of results per search, web and news together. Firecrawl "
            "bills every started block of 10 results: 2 credits, or 10 credits "
            "with end-to-end zero data retention (`zdr`). So 11 results cost "
            "twice as much as 10."
        ),
    )
    sources: Annotated[
        FirecrawlSourceChoice,
        NoneToDefault,
        RJSFMetaTag({"ui:enumNames": ["Web", "News", "Web and news"]}),
    ] = Field(
        default="web",
        title="Sources",
        description=(
            "Web searches regular web pages, News searches news articles. Web "
            "and news searches both: each source returns the full result "
            "count, so up to twice the results and the cost. The time filter "
            "does not apply to news."
        ),
    )
    highlights: bool = Field(
        default=True,
        title="Query-matched previews",
        description=(
            "Firecrawl replaces each result's preview with the passages of the "
            "page that match the query, which can be a whole table. Off "
            "returns the website's short description. Searches with zero data "
            "retention always return the short description."
        ),
    )
    safe_search: bool = Field(
        default=False,
        title="Safe search",
        description="Filter explicit content from the results.",
    )
    sort_by_date: bool = Field(
        default=False,
        title="Sort by date",
        description="Return the newest web results first instead of the best matches.",
    )
    zero_data_retention: Annotated[
        FirecrawlSearchZeroDataRetention,
        NoneToDefault,
        RJSFMetaTag(
            {
                "ui:enumNames": [
                    "As deployed",
                    "At least anonymized (anon)",
                    "End to end (zdr)",
                ]
            }
        ),
    ] = Field(
        default="deployment",
        title="Zero data retention",
        description=(
            "Raise zero data retention for this configuration above what the "
            "Search Proxy is deployed with. It can never lower it. `anon` "
            "costs 2 credits per 10 results, `zdr` 10. Firecrawl must have "
            "enabled the mode for the account, otherwise every search fails."
        ),
    )
    exclude_domains: Annotated[list[str], NoneToDefault] = Field(
        default_factory=list,
        max_length=100,
        title="Exclude domains",
        description=(
            "Never return results from these hostnames, for example "
            "`example.com`. Not exposed to the model."
        ),
        json_schema_extra={"type": ["array", "null"]},
    )

    time_filter: ExposableTimeFilter = Field(
        default=ExposableTimeFilter(expose=True, value=None),
        title="Time filter",
        description=(
            "Only return web results from the past hour (`qdr:h`), day "
            "(`qdr:d`), week (`qdr:w`), month (`qdr:m`) or year (`qdr:y`). "
            "Does not filter news results."
        ),
    )
    country: ExposableCountry = Field(
        default=ExposableCountry(expose=False, value=None),
        title="Country",
        description=(
            "ISO 3166-1 alpha-2 country code that results are localised for, "
            "for example `CH`. Unset uses Firecrawl's default, `US`."
        ),
    )
    location: ExposableLocation = Field(
        default=ExposableLocation(expose=False, value=None),
        title="Location",
        description=(
            "Location that results are localised for, for example "
            "`Zurich,Switzerland`. Set together with the country."
        ),
    )
    include_domains: ExposableDomainList = Field(
        default=ExposableDomainList(expose=False, value=None),
        title="Include domains",
        description=(
            "Only return results from these hostnames, for example `snb.ch`. "
            "Excluded domains are removed from this list."
        ),
    )
    category: ExposableCategory = Field(
        default=ExposableCategory(expose=False, value=None),
        title="Category",
        description=(
            "Only return one kind of web result: `research` (academic and "
            "research sites), `pdf` (PDF documents), `gov` (government "
            "publications, which cost no search credits) or `developer` "
            "(developer sites)."
        ),
    )


FirecrawlSearchRequest = FirecrawlSearchConfig.request_model()


__all__ = [
    "FIRECRAWL_MAX_QUERY_LENGTH",
    "FIRECRAWL_MAX_RESULTS",
    "FIRECRAWL_SOURCES",
    "ExposableCategory",
    "ExposableCountry",
    "ExposableDomainList",
    "ExposableLocation",
    "ExposableTimeFilter",
    "FirecrawlSearchConfig",
    "FirecrawlSearchRequest",
    "FirecrawlCategory",
    "FirecrawlSearchZeroDataRetention",
    "FirecrawlSearchSource",
    "FirecrawlSourceChoice",
    "FirecrawlTimeFilter",
]
