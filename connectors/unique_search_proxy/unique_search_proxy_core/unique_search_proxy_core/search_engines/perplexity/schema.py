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

PerplexitySearchContextSize: TypeAlias = Literal["low", "medium", "high"]
PerplexityRecencyFilter: TypeAlias = Literal["hour", "day", "week", "month", "year"]


IntOrNone: TypeAlias = Annotated[int | None, DeactivatedNone]

StrOrNone: TypeAlias = Annotated[str | None, DeactivatedNone]
SearchContextSizeOrNone: TypeAlias = Annotated[
    PerplexitySearchContextSize | None,
    DeactivatedNone,
]
RecencyFilterOrNone: TypeAlias = Annotated[
    PerplexityRecencyFilter | None, DeactivatedNone
]
LanguageFilterOrNone: TypeAlias = Annotated[list[str] | None, DeactivatedNone]
DomainFilterOrNone: TypeAlias = Annotated[list[str] | None, DeactivatedNone]

ExposableStrOrNone = ExposableParam[StrOrNone]
ExposableSearchContextSize = ExposableParam[SearchContextSizeOrNone]
ExposableRecencyFilter = ExposableParam[RecencyFilterOrNone]
ExposableLanguageFilter = ExposableParam[LanguageFilterOrNone]
ExposableDomainFilter = ExposableParam[DomainFilterOrNone]


def _inactive_str_exposable() -> ExposableStrOrNone:
    return ExposableStrOrNone(expose=False, value=None)


def _inactive_search_context_size_exposable() -> ExposableSearchContextSize:
    return ExposableSearchContextSize(expose=False, value=None)


def _inactive_recency_filter_exposable() -> ExposableRecencyFilter:
    return ExposableRecencyFilter(expose=False, value=None)


def _inactive_language_filter_exposable() -> ExposableLanguageFilter:
    return ExposableLanguageFilter(expose=False, value=None)


def _inactive_domain_filter_exposable() -> ExposableDomainFilter:
    return ExposableDomainFilter(expose=False, value=None)


class PerplexityConfig(BaseSearchEngineConfig[Literal[SearchEngineType.PERPLEXITY]]):
    """Single source of truth for Perplexity deployment + derived request/LLM surfaces.

    Field names mirror the Perplexity Search API request body
    (``POST https://api.perplexity.ai/search``).
    """

    engine: Literal[SearchEngineType.PERPLEXITY] = Field(
        default=SearchEngineType.PERPLEXITY,
        title="Search engine",
        description="Provider discriminator; must be `perplexity` for this config.",
    )

    max_tokens: IntOrNone = Field(
        default=None,
        ge=1,
        le=1_000_000,
        title="Max tokens",
        description=(
            "Maximum total webpage content tokens across all results "
            "(Perplexity `max_tokens`). Omitted when unset. "
            "Omit `search_context_size` when using this or `max_tokens_per_page`."
        ),
    )
    max_tokens_per_page: IntOrNone = Field(
        default=None,
        ge=1,
        le=1_000_000,
        alias="maxTokensPerPage",
        title="Max tokens per page",
        description=(
            "Maximum webpage content tokens extracted from each result page "
            "(Perplexity `max_tokens_per_page`). Omitted when unset. "
            "Omit `search_context_size` when using this or `max_tokens`."
        ),
    )

    country: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        title="Country",
        description=(
            "ISO 3166-1 alpha-2 country code (Perplexity `country`, two letters). "
            "Set `value` for a fixed default; set `expose` so the LLM may override per query."
        ),
    )
    search_context_size: ExposableSearchContextSize = Field(
        default_factory=_inactive_search_context_size_exposable,
        alias="searchContextSize",
        title="Search context size",
        description=(
            "Controls how much content is extracted from result pages: "
            "`low`, `medium`, or `high` (API default). "
            "Omit when using `max_tokens` or `max_tokens_per_page`. "
            "`value` + `expose` behave like `country`."
        ),
    )
    search_language_filter: ExposableLanguageFilter = Field(
        default_factory=_inactive_language_filter_exposable,
        alias="searchLanguageFilter",
        title="Search language filter",
        description=(
            "ISO 639-1 language codes (two characters each, up to 20). "
            "`value` + `expose` behave like `country`."
        ),
    )
    search_domain_filter: ExposableDomainFilter = Field(
        default_factory=_inactive_domain_filter_exposable,
        alias="searchDomainFilter",
        title="Search domain filter",
        description=(
            "Limit results to specific domains (up to 20). "
            "`value` + `expose` behave like `country`."
        ),
    )
    search_recency_filter: ExposableRecencyFilter = Field(
        default_factory=_inactive_recency_filter_exposable,
        alias="searchRecencyFilter",
        title="Search recency filter",
        description=(
            "Filter by publication recency: `hour`, `day`, `week`, `month`, or `year`. "
            "`value` + `expose` behave like `country`."
        ),
    )
    last_updated_after_filter: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        alias="lastUpdatedAfterFilter",
        title="Last updated after",
        description=(
            "Return results updated after this date (Perplexity `last_updated_after_filter`, "
            "input format `MM/DD/YYYY`). `value` + `expose` behave like `country`."
        ),
    )
    last_updated_before_filter: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        alias="lastUpdatedBeforeFilter",
        title="Last updated before",
        description=(
            "Return results updated before this date (Perplexity `last_updated_before_filter`, "
            "input format `MM/DD/YYYY`). `value` + `expose` behave like `country`."
        ),
    )
    search_after_date_filter: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        alias="searchAfterDateFilter",
        title="Search after date",
        description=(
            "Return results published after this date (Perplexity `search_after_date_filter`, "
            "input format `MM/DD/YYYY`). `value` + `expose` behave like `country`."
        ),
    )
    search_before_date_filter: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        alias="searchBeforeDateFilter",
        title="Search before date",
        description=(
            "Return results published before this date (Perplexity `search_before_date_filter`, "
            "input format `MM/DD/YYYY`). `value` + `expose` behave like `country`."
        ),
    )


def perplexity_request_model() -> type[BaseModel]:
    """Derived ``POST /v1/search`` model (cached via ``build_request_model``)."""
    return build_request_model(PerplexityConfig)


PerplexitySearchRequest = perplexity_request_model()


__all__ = [
    "ExposableDomainFilter",
    "ExposableLanguageFilter",
    "ExposableRecencyFilter",
    "ExposableSearchContextSize",
    "ExposableStrOrNone",
    "PerplexityConfig",
    "PerplexitySearchRequest",
    "PerplexityRecencyFilter",
    "PerplexitySearchContextSize",
    "perplexity_request_model",
]
