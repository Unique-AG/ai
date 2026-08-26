from __future__ import annotations

from typing import Annotated, Any, ClassVar, Literal, TypeAlias

from pydantic import Field, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.agent_engines.base import (
    AgentEngineType,
    BaseAgentEngineConfig,
)
from unique_search_proxy_core.agent_engines.bing.settings import (
    bing_agent_env_settings,
)
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.schema import DeactivatedNone

_BING_DOCS_BASE_URL = (
    "https://learn.microsoft.com/en-us/previous-versions/bing/search-apis/"
    "bing-web-search/reference"
)
_BING_QUERY_PARAMS_DOCS_URL = f"{_BING_DOCS_BASE_URL}/query-parameters"
_BING_MARKET_CODES_DOCS_URL = f"{_BING_DOCS_BASE_URL}/market-codes"

#: Markets Bing serves content for (``mkt``), in the documented order.
BingMarket: TypeAlias = Literal[
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

#: Languages Bing localizes its interface strings into (``setLang``).
BingSetLang: TypeAlias = Literal[
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

#: Named recency windows accepted by the Bing ``freshness`` knob.
BingFreshnessPreset: TypeAlias = Literal["Day", "Week", "Month"]

_FRESHNESS_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}(?:\.\.\d{4}-\d{2}-\d{2})?$"


class BingFreshnessDate(str):
    """A single ``YYYY-MM-DD`` day or an inclusive ``YYYY-MM-DD..YYYY-MM-DD`` span.

    The constraint lives in the type instead of ``Field(pattern=...)`` because
    request-model derivation strips ``Annotated`` metadata off union branches,
    which would leave exactly the surface the LLM writes to unchecked. Freshness
    is baked into the hashed agent name, so free text here would mint a Foundry
    agent version per distinct string while Bing ignored the value itself.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.str_schema(pattern=_FRESHNESS_DATE_PATTERN)


MarketOrNone: TypeAlias = Annotated[BingMarket, Field(title="Market")] | DeactivatedNone
SetLangOrNone: TypeAlias = (
    Annotated[BingSetLang, Field(title="Language")] | DeactivatedNone
)
FreshnessOrNone: TypeAlias = (
    Annotated[BingFreshnessPreset, Field(title="Preset")]
    | Annotated[BingFreshnessDate, Field(title="Day or range")]
    | DeactivatedNone
)

ExposableMarket = ExposableParam[MarketOrNone]
ExposableSetLang = ExposableParam[SetLangOrNone]
ExposableFreshness = ExposableParam[FreshnessOrNone]


def _default_market() -> ExposableMarket:
    return ExposableMarket(
        expose=False,
        value=bing_agent_env_settings.default_market,
    )


class BingAgentConfig(BaseAgentEngineConfig[Literal[AgentEngineType.BING]]):
    """Deployment + request defaults for Bing grounding via Azure AI Projects."""

    _request_model_name: ClassVar[str] = "BingAgentSearchRequest"
    _exposed_params_model_name: ClassVar[str] = "BingAgentExposedParams"

    engine: Annotated[
        Literal[AgentEngineType.BING], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=AgentEngineType.BING,
        title="Agent engine",
        description="Provider discriminator; must be `bing` for this config.",
    )
    fetch_size: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of Bing grounding results per query",
    )
    market: ExposableMarket = Field(
        default_factory=_default_market,
        title="Market",
        description=(
            "Country/region **and** language the results come from (Bing `mkt`), "
            "as `<language>-<country>`: `de-CH` returns German-language Swiss "
            "results, `fr-CH` French-language Swiss ones, `en-GB` UK English. "
            "Set it when the question is about a specific country or expects an "
            "answer in that country's language. Left unset, Bing guesses the "
            "market from the caller and may answer from another country. "
            f"[Market codes]({_BING_MARKET_CODES_DOCS_URL})"
        ),
    )
    set_lang: ExposableSetLang = Field(
        default=ExposableSetLang(expose=False, value=None),
        title="Interface language",
        description=(
            "Language of Bing's own interface strings in the response (Bing "
            "`setLang`), e.g. `de`, `fr`, `pt-br`. It changes neither which "
            "results come back nor the language they are written in — use the "
            "market for that. Bing falls back to English for codes it does not "
            "support. "
            f"[Supported languages]({_BING_MARKET_CODES_DOCS_URL}#bing-supported-language-codes)"
        ),
    )
    freshness: ExposableFreshness = Field(
        default=ExposableFreshness(expose=False, value=None),
        title="Freshness",
        description=(
            "Keep only pages Bing discovered recently (Bing `freshness`): `Day` "
            "(last 24 hours), `Week` (last 7 days), `Month` (last 30 days), a "
            "single `YYYY-MM-DD` day, or an inclusive "
            "`YYYY-MM-DD..YYYY-MM-DD` range. Use it for news and fast-moving "
            "topics; leave it unset for background or reference questions, where "
            "it would hide older pages that are still correct. "
            f"[Accepted values]({_BING_QUERY_PARAMS_DOCS_URL}#freshness)"
        ),
    )


BingAgentSearchRequest = BingAgentConfig.request_model()


__all__ = [
    "BingAgentConfig",
    "BingAgentSearchRequest",
    "BingFreshnessDate",
    "BingFreshnessPreset",
    "BingMarket",
    "BingSetLang",
    "ExposableFreshness",
    "ExposableMarket",
    "ExposableSetLang",
]
