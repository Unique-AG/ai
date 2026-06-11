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

BraveSafesearch: TypeAlias = Literal["off", "moderate", "strict"]
BraveUnits: TypeAlias = Literal["metric", "imperial"]

StrOrNone: TypeAlias = Annotated[str | None, DeactivatedNone]
SafesearchOrNone: TypeAlias = Annotated[BraveSafesearch | None, DeactivatedNone]
ResultFilterOrNone: TypeAlias = Annotated[list[str] | None, DeactivatedNone]

ExposableStrOrNone = ExposableParam[StrOrNone]
ExposableSafesearch = ExposableParam[SafesearchOrNone]
ExposableResultFilter = ExposableParam[ResultFilterOrNone]


def _inactive_str_exposable() -> ExposableStrOrNone:
    return ExposableStrOrNone(expose=False, value=None)


def _inactive_result_filter_exposable() -> ExposableResultFilter:
    return ExposableResultFilter(expose=False, value=None)


def _default_safesearch_exposable() -> ExposableSafesearch:
    return ExposableSafesearch(expose=False, value="moderate")


class BraveConfig(BaseSearchEngineConfig[Literal[SearchEngineType.BRAVE]]):
    """Single source of truth for Brave deployment + derived request/LLM surfaces."""

    engine: Literal[SearchEngineType.BRAVE] = Field(
        default=SearchEngineType.BRAVE,
        title="Search engine",
        description="Provider discriminator; must be `brave` for this config.",
    )

    extra_snippets: bool = Field(
        default=False,
        title="Extra snippets",
        description=(
            "Request up to five additional alternative excerpts per result (Brave `extra_snippets`)."
        ),
    )
    spellcheck: bool = Field(
        default=True,
        title="Spellcheck",
        description="Whether Brave spell-checks the query and uses the corrected form.",
    )
    text_decorations: bool = Field(
        default=True,
        title="Text decorations",
        description="Whether result snippets include decoration markers (e.g. highlighting).",
    )
    operators: bool = Field(
        default=True,
        title="Search operators",
        description="Whether Brave applies search operators in the query.",
    )
    ui_lang: str = Field(
        default="en-US",
        title="UI language",
        description=(
            "User interface language for response strings (Brave `ui_lang`), "
            "e.g. `en-US`. Distinct from `search_lang`."
        ),
    )
    units: BraveUnits | None = Field(
        default=None,
        title="Measurement units",
        description="Measurement units for location-rich results: `metric` or `imperial`.",
    )
    summary: bool = Field(
        default=True,
        title="Summary",
        description="Enable summary key generation in web search results (Brave summarizer).",
    )
    include_fetch_metadata: bool = Field(
        default=False,
        title="Include fetch metadata",
        description="Include fetch metadata in the Brave response.",
    )
    goggles: str | list[str] | None = Field(
        default=None,
        title="Goggles",
        description=(
            "Custom re-ranking Goggle URL(s) or definition(s). Up to three Goggles per request."
        ),
    )

    country: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        title="Country",
        description=(
            "Two-letter ISO 3166-1 alpha-2 country code for result origin (Brave `country`). "
            "Set `value` for a fixed default; set `expose` so the LLM may override per query."
        ),
    )
    freshness: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        title="Freshness",
        description=(
            "Recency filter: `pd`, `pw`, `pm`, `py`, or `YYYY-MM-DDtoYYYY-MM-DD`. "
            "`value` + `expose` behave like `country`."
        ),
    )
    search_lang: ExposableStrOrNone = Field(
        default_factory=_inactive_str_exposable,
        alias="searchLang",
        title="Search language",
        description=(
            "Language code for result documents (Brave `search_lang`). "
            "`value` + `expose` behave like `country`."
        ),
    )
    safesearch: ExposableSafesearch = Field(
        default_factory=_default_safesearch_exposable,
        title="Safe search",
        description=(
            "Adult content filter: `off`, `moderate` (API default), or `strict`. "
            "Usually set via admin `value`; enable `expose` only if the LLM may tune per query."
        ),
    )
    result_filter: ExposableResultFilter = Field(
        default_factory=_inactive_result_filter_exposable,
        alias="resultFilter",
        title="Result filter",
        description=(
            "Result types to include, e.g. `web`, `news`, `videos`. "
            "Omit (`null`) for all subscribed types. `value` + `expose` behave like `country`."
        ),
    )


def brave_request_model() -> type[BaseModel]:
    """Derived ``POST /v1/search`` model (cached via ``build_request_model``)."""
    return build_request_model(BraveConfig)


BraveRequest = brave_request_model()


__all__ = [
    "BraveConfig",
    "BraveRequest",
    "BraveSafesearch",
    "BraveUnits",
    "ExposableResultFilter",
    "ExposableSafesearch",
    "ExposableStrOrNone",
    "brave_request_model",
]
