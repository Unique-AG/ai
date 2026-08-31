from __future__ import annotations

from typing import Annotated, Any, ClassVar, Literal, get_args

from pydantic import Field, GetCoreSchemaHandler, GetJsonSchemaHandler
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
    BingSetLang,
)

_BING_DOCS_BASE_URL = (
    "https://learn.microsoft.com/en-us/previous-versions/bing/search-apis/"
    "bing-web-search/reference"
)
_BING_QUERY_PARAMS_DOCS_URL = f"{_BING_DOCS_BASE_URL}/query-parameters"
_BING_MARKET_CODES_DOCS_URL = f"{_BING_DOCS_BASE_URL}/market-codes"

_FRESHNESS_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}(?:\.\.\d{4}-\d{2}-\d{2})?$"


class BingFreshnessDate(str):
    """A single ``YYYY-MM-DD`` day or an inclusive ``YYYY-MM-DD..YYYY-MM-DD`` span."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source: type[Any],
        handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.str_schema(pattern=_FRESHNESS_DATE_PATTERN)


def _optional_enum_schema(
    property_schema: JsonSchemaValue,
    *,
    values: tuple[Any, ...],
    empty_title: str,
) -> JsonSchemaValue:
    """Render an optional literal as one dropdown instead of an RJSF union selector."""
    schema = dict(property_schema)
    schema.pop("anyOf", None)
    schema["type"] = ["string", "null"]
    schema["oneOf"] = [
        {"const": None, "title": empty_title},
        *({"const": value, "title": value} for value in values),
    ]
    return schema


class BingAgentConfig(BaseAgentEngineConfig[Literal[AgentEngineType.BING]]):
    """Deployment configuration for Bing grounding via Azure AI Projects."""

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
    market: BingMarket | None = Field(
        default=None,
        title="Market",
        description=(
            "Optional fixed country/region and language for Bing search results "
            "(Bing `mkt`). For example, `de-CH` returns German-language results "
            "from Switzerland, while `fr-CH` returns French-language results "
            "from Switzerland. The selected value applies to every search in this "
            "space and cannot be changed by the assistant. Leave blank to omit the "
            "market parameter. "
            f"[View supported market codes]({_BING_MARKET_CODES_DOCS_URL})."
        ),
    )
    set_lang: BingSetLang | None = Field(
        default=None,
        title="Interface language",
        description=(
            "Optional fixed language for Bing's own interface strings in the response "
            "(Bing `setLang`), e.g. `de`, `fr`, `pt-br`. It changes neither which "
            "results come back nor the language they are written in — use Market for "
            "that. The selected value applies to every search in this space and cannot "
            "be changed by the assistant. Leave blank to omit the interface language "
            "parameter. "
            f"[Supported languages]({_BING_MARKET_CODES_DOCS_URL}#bing-supported-language-codes)"
        ),
    )
    freshness: Annotated[
        BingFreshnessPreset | BingFreshnessDate | None,
        RJSFMetaTag(
            {
                "ui:widget": "text",
                "ui:placeholder": (
                    "Day, Week, Month, YYYY-MM-DD, or YYYY-MM-DD..YYYY-MM-DD"
                ),
                "ui:emptyValue": None,
            }
        ),
    ] = Field(
        default=None,
        title="Freshness",
        description=(
            "Optional fixed recency filter for every search in this space (Bing "
            "`freshness`): `Day` (last 24 hours), `Week` (last 7 days), `Month` "
            "(last 30 days), a single `YYYY-MM-DD` day, or an inclusive "
            "`YYYY-MM-DD..YYYY-MM-DD` range. The assistant cannot change this value. "
            "Leave blank to omit the freshness parameter. "
            f"[Accepted values]({_BING_QUERY_PARAMS_DOCS_URL}#freshness)"
        ),
    )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Keep optional Bing fields simple and quiet in the live admin form."""
        schema = handler(core_schema)
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            return schema

        market = properties.get("market")
        if isinstance(market, dict):
            properties["market"] = _optional_enum_schema(
                market,
                values=get_args(BingMarket),
                empty_title="No fixed market",
            )

        set_lang = properties.get("setLang")
        if isinstance(set_lang, dict):
            properties["setLang"] = _optional_enum_schema(
                set_lang,
                values=get_args(BingSetLang),
                empty_title="No fixed interface language",
            )

        freshness = properties.get("freshness")
        if isinstance(freshness, dict):
            # Allow incomplete text during live editing. Pydantic still validates the
            # preset/date syntax when the configuration is submitted.
            freshness = dict(freshness)
            freshness.pop("anyOf", None)
            freshness["type"] = ["string", "null"]
            properties["freshness"] = freshness

        return schema


BingAgentSearchRequest = BingAgentConfig.request_model()


__all__ = [
    "BingAgentConfig",
    "BingAgentSearchRequest",
    "BingFreshnessDate",
    "BingFreshnessPreset",
    "BingMarket",
    "BingSetLang",
]
