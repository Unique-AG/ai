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

PerplexitySearchContextSize: TypeAlias = Literal["low", "medium", "high"]
PerplexityRecencyFilter: TypeAlias = Literal["hour", "day", "week", "month", "year"]

IntOrNone: TypeAlias = (
    Annotated[int, Field(title="Integer", ge=1, le=1_000_000)] | DeactivatedNone
)
StrOrNone: TypeAlias = Annotated[str, Field(title="String")] | DeactivatedNone
RecencyFilterOrNone: TypeAlias = (
    Annotated[PerplexityRecencyFilter, Field(title="Recency Filter")] | DeactivatedNone
)
LanguageFilterOrNone: TypeAlias = (
    Annotated[list[str], Field(title="Language Filter")] | DeactivatedNone
)
DomainFilterOrNone: TypeAlias = (
    Annotated[list[str], Field(title="Domain Filter")] | DeactivatedNone
)

ExposableStrOrNone = ExposableParam[StrOrNone]
ExposableRecencyFilter = ExposableParam[RecencyFilterOrNone]
ExposableLanguageFilter = ExposableParam[LanguageFilterOrNone]
ExposableDomainFilter = ExposableParam[DomainFilterOrNone]


class PerplexityConfig(BaseSearchEngineConfig[Literal[SearchEngineType.PERPLEXITY]]):
    """Single source of truth for Perplexity deployment + derived request/LLM surfaces.

    Field names mirror the Perplexity Search API request body
    (``POST https://api.perplexity.ai/search``).
    """

    _request_model_name: ClassVar[str] = "PerplexitySearchRequest"
    _exposed_params_model_name: ClassVar[str] = "PerplexityExposedParams"

    engine: Annotated[
        Literal[SearchEngineType.PERPLEXITY], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=SearchEngineType.PERPLEXITY,
        title="Search engine",
        description="Provider discriminator; must be `perplexity` for this config.",
    )

    max_tokens: IntOrNone = Field(
        default=None,
        title="Max tokens",
        description=(
            "Maximum total webpage content tokens across all results "
            "(Perplexity `max_tokens`). Omitted when unset. "
            "Omit `search_context_size` when using this or `max_tokens_per_page`."
        ),
    )
    max_tokens_per_page: IntOrNone = Field(
        default=None,
        alias="maxTokensPerPage",
        title="Max tokens per page",
        description=(
            "Maximum webpage content tokens extracted from each result page "
            "(Perplexity `max_tokens_per_page`). Omitted when unset. "
            "Omit `search_context_size` when using this or `max_tokens`."
        ),
    )
    search_context_size: PerplexitySearchContextSize = Field(
        default="medium",
        alias="searchContextSize",
        title="Search context size",
        description=(
            "How much content is extracted from result pages (Perplexity `search_context_size`): "
            "`low`, `medium`, or `high` (API default). "
            "Omit when using `max_tokens` or `max_tokens_per_page`."
        ),
    )

    country: ExposableStrOrNone = Field(
        default=ExposableStrOrNone(expose=False, value=None),
        title="Country",
        description="ISO 3166-1 alpha-2 country code (Perplexity `country`, two letters).",
    )
    search_language_filter: ExposableLanguageFilter = Field(
        default=ExposableLanguageFilter(expose=False, value=None),
        alias="searchLanguageFilter",
        title="Search language filter",
        description=(
            "ISO 639-1 language codes to include (Perplexity `search_language_filter`; "
            "two characters each, up to 20)."
        ),
    )
    search_domain_filter: ExposableDomainFilter = Field(
        default=ExposableDomainFilter(expose=False, value=None),
        alias="searchDomainFilter",
        title="Search domain filter",
        description=(
            "Domains to limit results to (Perplexity `search_domain_filter`; up to 20)."
        ),
    )
    search_recency_filter: ExposableRecencyFilter = Field(
        default=ExposableRecencyFilter(expose=False, value=None),
        alias="searchRecencyFilter",
        title="Search recency filter",
        description=(
            "Publication recency filter (Perplexity `search_recency_filter`): "
            "`hour`, `day`, `week`, `month`, or `year`."
        ),
    )
    last_updated_after_filter: ExposableStrOrNone = Field(
        default=ExposableStrOrNone(expose=False, value=None),
        alias="lastUpdatedAfterFilter",
        title="Last updated after",
        description=(
            "Return results updated after this date (Perplexity `last_updated_after_filter`; "
            "format `MM/DD/YYYY`)."
        ),
    )
    last_updated_before_filter: ExposableStrOrNone = Field(
        default=ExposableStrOrNone(expose=False, value=None),
        alias="lastUpdatedBeforeFilter",
        title="Last updated before",
        description=(
            "Return results updated before this date (Perplexity `last_updated_before_filter`; "
            "format `MM/DD/YYYY`)."
        ),
    )
    search_after_date_filter: ExposableStrOrNone = Field(
        default=ExposableStrOrNone(expose=False, value=None),
        alias="searchAfterDateFilter",
        title="Search after date",
        description=(
            "Return results published after this date (Perplexity `search_after_date_filter`; "
            "format `MM/DD/YYYY`)."
        ),
    )
    search_before_date_filter: ExposableStrOrNone = Field(
        default=ExposableStrOrNone(expose=False, value=None),
        alias="searchBeforeDateFilter",
        title="Search before date",
        description=(
            "Return results published before this date (Perplexity `search_before_date_filter`; "
            "format `MM/DD/YYYY`)."
        ),
    )


PerplexitySearchRequest = PerplexityConfig.request_model()


__all__ = [
    "ExposableDomainFilter",
    "ExposableLanguageFilter",
    "ExposableRecencyFilter",
    "ExposableStrOrNone",
    "PerplexityConfig",
    "PerplexitySearchRequest",
    "PerplexityRecencyFilter",
    "PerplexitySearchContextSize",
]
