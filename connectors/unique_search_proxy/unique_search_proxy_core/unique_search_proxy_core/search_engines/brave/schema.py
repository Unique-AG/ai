from __future__ import annotations

from typing import Annotated, ClassVar, Literal, TypeAlias, get_args

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.schema import DeactivatedNone
from unique_search_proxy_core.search_engines.base import (
    BaseSearchEngineConfig,
    SearchEngineType,
)

BraveSafesearch: TypeAlias = Literal["off", "moderate", "strict"]
BraveUnits: TypeAlias = Literal["metric", "imperial"]

BraveCountry: TypeAlias = Literal[
    "AR",
    "AU",
    "AT",
    "BE",
    "BR",
    "CA",
    "CL",
    "DK",
    "FI",
    "FR",
    "DE",
    "GR",
    "HK",
    "IN",
    "ID",
    "IT",
    "JP",
    "KR",
    "MY",
    "MX",
    "NL",
    "NZ",
    "NO",
    "CN",
    "PL",
    "PT",
    "PH",
    "RU",
    "SA",
    "ZA",
    "ES",
    "SE",
    "CH",
    "TW",
    "TR",
    "GB",
    "US",
    "ALL",
]

BraveSearchLang: TypeAlias = Literal[
    "ar",
    "eu",
    "bn",
    "bg",
    "ca",
    "zh-hans",
    "zh-hant",
    "hr",
    "cs",
    "da",
    "nl",
    "en",
    "en-gb",
    "et",
    "fi",
    "fr",
    "gl",
    "de",
    "el",
    "gu",
    "he",
    "hi",
    "hu",
    "is",
    "it",
    "jp",
    "kn",
    "ko",
    "lv",
    "lt",
    "ms",
    "ml",
    "mr",
    "nb",
    "pl",
    "pt-br",
    "pt-pt",
    "pa",
    "ro",
    "ru",
    "sr",
    "sk",
    "sl",
    "es",
    "sv",
    "ta",
    "te",
    "th",
    "tr",
    "uk",
    "vi",
]

_BRAVE_COUNTRY_DESCRIPTION_SUFFIX = ", ".join(
    f"`{code}`" for code in get_args(BraveCountry)
)
_BRAVE_SEARCH_LANG_DESCRIPTION_SUFFIX = ", ".join(
    f"`{code}`" for code in get_args(BraveSearchLang)
)

BraveResultFilterType: TypeAlias = Literal[
    "discussions",
    "faq",
    "infobox",
    "news",
    "query",
    "summarizer",
    "videos",
    "web",
    "locations",
]

_BRAVE_RESULT_FILTER_DESCRIPTION_SUFFIX = ", ".join(
    f"`{code}`" for code in get_args(BraveResultFilterType)
)

_GOGGLES_DOCS_URL = (
    "https://api-dashboard.search.brave.com/documentation/resources/goggles"
)

BraveUiLang: TypeAlias = Literal[
    "es-AR",
    "en-AU",
    "de-AT",
    "nl-BE",
    "fr-BE",
    "pt-BR",
    "en-CA",
    "fr-CA",
    "es-CL",
    "da-DK",
    "fi-FI",
    "fr-FR",
    "de-DE",
    "el-GR",
    "zh-HK",
    "en-IN",
    "en-ID",
    "it-IT",
    "ja-JP",
    "ko-KR",
    "en-MY",
    "es-MX",
    "nl-NL",
    "en-NZ",
    "no-NO",
    "zh-CN",
    "pl-PL",
    "en-PH",
    "ru-RU",
    "en-ZA",
    "es-ES",
    "sv-SE",
    "fr-CH",
    "de-CH",
    "zh-TW",
    "tr-TR",
    "en-GB",
    "en-US",
    "es-US",
]

GogglesOrNone: TypeAlias = (
    Annotated[str, Field(title="String")]
    | Annotated[list[str], Field(title="Array")]
    | DeactivatedNone
)

BraveUnitsOrNone: TypeAlias = (
    Annotated[BraveUnits, Field(title="Brave Units")] | DeactivatedNone
)
StrOrNone: TypeAlias = Annotated[str, Field(title="String")] | DeactivatedNone
ResultFilterOrNone: TypeAlias = (
    Annotated[list[BraveResultFilterType], Field(title="Result Filter")]
    | DeactivatedNone
)

ExposableStrOrNone = ExposableParam[StrOrNone]
ExposableCountry = ExposableParam[BraveCountry]
ExposableSearchLang = ExposableParam[BraveSearchLang]
ExposableResultFilter = ExposableParam[ResultFilterOrNone]


class BraveConfig(BaseSearchEngineConfig[Literal[SearchEngineType.BRAVE]]):
    """Single source of truth for Brave deployment + derived request/LLM surfaces."""

    _request_model_name: ClassVar[str] = "BraveSearchRequest"
    _exposed_params_model_name: ClassVar[str] = "BraveExposedParams"

    engine: Annotated[
        Literal[SearchEngineType.BRAVE], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=SearchEngineType.BRAVE,
        title="Search engine",
        description="Provider discriminator; must be `brave` for this config.",
    )

    extra_snippets: bool = Field(
        default=True,
        title="Extra snippets",
        description=(
            "Request up to five additional alternative excerpts per result (Brave `extra_snippets`)."
        ),
    )
    spellcheck: bool = Field(
        default=False,
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
    ui_lang: BraveUiLang = Field(
        default="en-US",
        title="UI language",
        description=(
            "User interface language preferred in response. Usually of the format "
            "`<language_code>-<country_code>`. For more, see RFC 9110."
        ),
    )
    units: BraveUnitsOrNone = Field(
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

    safesearch: BraveSafesearch = Field(
        default="moderate",
        title="Safe search",
        description=(
            "Adult content filter: `off`, `moderate` (API default), or `strict`."
        ),
    )
    goggles: GogglesOrNone = Field(
        default=None,
        title="Goggles",
        description=(
            "Custom re-ranking Goggle URL(s) or definition(s). Up to three Goggles per request."
            f" [Learn more about Brave Goggles]({_GOGGLES_DOCS_URL})"
        ),
    )

    country: ExposableCountry = Field(
        default=ExposableCountry(expose=False, value="US"),
        title="Country",
        description=(
            "The 2 character country code where the search results come from. "
            f"Supported values: {_BRAVE_COUNTRY_DESCRIPTION_SUFFIX}."
        ),
    )
    freshness: ExposableStrOrNone = Field(
        default=ExposableStrOrNone(expose=False, value=None),
        title="Freshness",
        description=(
            "Recency filter (Brave `freshness`): `pd`, `pw`, `pm`, `py`, "
            "or `YYYY-MM-DDtoYYYY-MM-DD`."
        ),
    )
    search_lang: ExposableSearchLang = Field(
        default=ExposableSearchLang(expose=False, value="en"),
        alias="searchLang",
        title="Search language",
        description=(
            "The 2 or more character language code for which the search results "
            f"are provided. Supported values: {_BRAVE_SEARCH_LANG_DESCRIPTION_SUFFIX}."
        ),
    )
    result_filter: ExposableResultFilter = Field(
        default=ExposableResultFilter(expose=False, value=None),
        alias="resultFilter",
        title="Result filter",
        description=(
            "Result types to include in the search response (Brave `result_filter`). "
            "Omit for all result types allowed by the subscription. "
            f"Supported values: {_BRAVE_RESULT_FILTER_DESCRIPTION_SUFFIX}."
        ),
    )


BraveSearchRequest = BraveConfig.request_model()


__all__ = [
    "BraveConfig",
    "BraveCountry",
    "BraveResultFilterType",
    "BraveSearchLang",
    "BraveSearchRequest",
    "BraveSafesearch",
    "BraveUiLang",
    "BraveUnits",
    "ExposableCountry",
    "ExposableResultFilter",
    "ExposableSearchLang",
    "ExposableStrOrNone",
]
