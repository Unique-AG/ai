from __future__ import annotations

from typing import Annotated, Any, ClassVar, Generic, Literal, TypeAlias, TypeVar, cast

from pydantic import (
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    PrivateAttr,
    field_validator,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.agent_engines.base import (
    AgentEngineType,
    BaseAgentEngineConfig,
)
from unique_search_proxy_core.agent_engines.bing.enums import (
    BingFreshnessPreset,
    BingMarket,
    BingMarketSelection,
    BingSetLang,
)
from unique_search_proxy_core.agent_engines.bing.settings import (
    bing_agent_env_settings,
)
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.param_policy.ui_tags import dynamic_enforced_by_infra
from unique_search_proxy_core.schema import DeactivatedNone, camelized_model_config

_BING_DOCS_BASE_URL = (
    "https://learn.microsoft.com/en-us/previous-versions/bing/search-apis/"
    "bing-web-search/reference"
)
_BING_QUERY_PARAMS_DOCS_URL = f"{_BING_DOCS_BASE_URL}/query-parameters"
_BING_MARKET_CODES_DOCS_URL = f"{_BING_DOCS_BASE_URL}/market-codes"


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

ExposableSetLang = ExposableParam[SetLangOrNone]
ExposableFreshness = ExposableParam[FreshnessOrNone]


T = TypeVar("T")


class BingMarketParam(ExposableParam[T], Generic[T]):
    """Bing-specific admin policy projected onto the generic parameter lifecycle."""

    model_config = ConfigDict(**camelized_model_config, extra="forbid")

    _expose: bool = PrivateAttr(default=False)
    _value: T | None = PrivateAttr(default=None)
    expose: ClassVar[property] = property(lambda self: self._expose)
    value: ClassVar[property] = property(lambda self: self._value)
    enabled: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(title="Enable market parameter"),
    ] = Field(
        default=False,
        title="Enable market parameter",
        description=(
            "Include a Bing market when fixed below, or let the agent choose one."
        ),
    )
    agent_controlled: Annotated[
        bool,
        RJSFMetaTag.BooleanWidget.checkbox(title="Agent controlled parameter"),
    ] = Field(
        default=False,
        title="Agent controlled parameter",
        description=(
            "Allow the agent to choose an optional Bing market for each search. "
            "When the agent omits it, no market is sent."
        ),
    )
    market: BingMarketSelection = Field(
        default=BingMarketSelection.DEFAULT,
        title="Market",
        description=(
            "Select a fixed Bing market. Default uses `BING_AGENT_MARKET.default`; "
            "if that setting is unset, no market is sent and Bing infers it."
        ),
    )

    @classmethod
    def model_parametrized_name(cls, params: tuple[type[Any], ...]) -> str:
        return "BingMarketConfig"

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Show dependent controls using standard RJSF conditional-schema support."""
        schema = handler(core_schema)
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            return schema

        agent_key = (
            "agentControlled" if "agentControlled" in properties else "agent_controlled"
        )
        enabled = properties.get("enabled")
        agent_controlled = properties.get(agent_key)
        market = properties.get("market")
        if enabled is None or agent_controlled is None or market is None:
            return schema

        schema.pop("additionalProperties", None)
        schema["properties"] = {"enabled": enabled}
        schema["allOf"] = [
            {
                "if": {
                    "properties": {"enabled": {"const": True}},
                    "required": ["enabled"],
                },
                "then": {
                    "properties": {agent_key: agent_controlled},
                    "allOf": [
                        {
                            "if": {
                                "properties": {
                                    agent_key: {"const": False},
                                },
                            },
                            "then": {"properties": {"market": market}},
                        },
                    ],
                },
            },
        ]
        return schema

    @model_validator(mode="before")
    @classmethod
    def prefer_agent_controlled_alias(cls, data: Any) -> Any:
        """Let a submitted camel-case value override merged factory defaults."""
        if not isinstance(data, dict) or "agentControlled" not in data:
            return data
        normalized = dict(data)
        normalized["agent_controlled"] = normalized.pop("agentControlled")
        return normalized

    @model_validator(mode="after")
    def resolve_policy(self) -> BingMarketParam[T]:
        """Populate the generic runtime fields without serializing resolved defaults."""
        self._expose = self.enabled and self.agent_controlled
        if not self.enabled or self.agent_controlled:
            runtime_value: str | None = None
        elif self.market is BingMarketSelection.DEFAULT:
            runtime_value = bing_agent_env_settings.market.default
        else:
            runtime_value = self.market.value
        self._value = cast(T, runtime_value)
        return self


BingMarketConfig = BingMarketParam[MarketOrNone]


def _market_is_enforced() -> bool:
    return bing_agent_env_settings.market.enforce


def _default_market() -> BingMarketConfig:
    return BingMarketConfig(
        enabled=bing_agent_env_settings.market.enforce,
        agent_controlled=False,
        market=BingMarketSelection.DEFAULT,
    )


EnforcedBingMarketConfig = Annotated[
    BingMarketConfig,
    dynamic_enforced_by_infra(
        _market_is_enforced,
        help=(
            "Market controls are pinned to Default for this deployment by "
            '`BING_AGENT_MARKET={"default": "<mkt>", "enforce": true}`.'
        ),
    ),
]


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
    market: EnforcedBingMarketConfig = Field(
        default_factory=_default_market,
        title="Market",
        description=(
            "Country/region **and** language the results come from (Bing `mkt`), "
            "as `<language>-<country>`: `de-CH` returns German-language Swiss "
            "results, `fr-CH` French-language Swiss ones, `en-GB` UK English. "
            "Set a fixed market when every question targets one country, let the "
            "agent choose per search, or select Default to use "
            "`BING_AGENT_MARKET.default`. With no resolved market, Bing infers it "
            "and may answer from another country. "
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

    @field_validator("market", mode="before")
    @classmethod
    def validate_market(cls, v: Any) -> Any:
        if bing_agent_env_settings.market.enforce:
            return {
                "enabled": True,
                "agentControlled": False,
                "market": BingMarketSelection.DEFAULT,
            }
        return v


BingAgentSearchRequest = BingAgentConfig.request_model()


__all__ = [
    "BingAgentConfig",
    "BingAgentSearchRequest",
    "BingFreshnessDate",
    "BingFreshnessPreset",
    "BingMarket",
    "BingMarketConfig",
    "BingMarketSelection",
    "BingSetLang",
    "ExposableFreshness",
    "ExposableSetLang",
]
