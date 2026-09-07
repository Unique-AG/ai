from __future__ import annotations

from typing import Annotated, Any, ClassVar, Literal, Mapping, get_args

from pydantic import Field, GetJsonSchemaHandler, field_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.agent_engines.base import (
    AgentEngineType,
    BaseAgentEngineConfig,
)
from unique_search_proxy_core.agent_engines.bing.enums import (
    BingFreshnessPreset,
    BingMarket,
)

_BING_DOCS_BASE_URL = (
    "https://learn.microsoft.com/en-us/previous-versions/bing/search-apis/"
    "bing-web-search/reference"
)
_BING_QUERY_PARAMS_DOCS_URL = f"{_BING_DOCS_BASE_URL}/query-parameters"

#: Admin-facing labels for the recency presets, whose wire values are terse.
_FRESHNESS_PRESET_TITLES: Mapping[str, str] = {
    "Day": "Past 24 hours",
    "Week": "Past 7 days",
    "Month": "Past 30 days",
}


def _single_dropdown(
    property_schema: JsonSchemaValue,
    *,
    values: tuple[Any, ...],
    blank_title: str,
    titles: Mapping[Any, str] | None = None,
) -> JsonSchemaValue:
    """Render an optional literal as one dropdown instead of a union selector.

    ``Literal[...] | None`` reaches RJSF as an ``anyOf``, drawn as a branch
    picker wrapping a second control; a single ``oneOf`` of constants collapses
    that into one select whose first entry is the blank value. ``titles``
    relabels options whose wire values are not admin-facing copy.
    """
    schema = dict(property_schema)
    schema.pop("anyOf", None)
    schema["type"] = ["string", "null"]
    schema["oneOf"] = [
        {"const": None, "title": blank_title},
        *(
            {"const": value, "title": (titles or {}).get(value, value)}
            for value in values
        ),
    ]
    return schema


class BingAgentConfig(BaseAgentEngineConfig[Literal[AgentEngineType.BING]]):
    """Deployment + request defaults for Bing grounding via Azure AI Projects.

    The grounding knobs are fixed values chosen by an admin: whatever is set
    here applies to every search in the space and is never offered to the LLM
    to steer per call.
    """

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
    search_market: BingMarket | None = Field(
        default=None,
        title="Preferred region and language",
        description=(
            "Region and language Bing should favour, as `<language>-<country>`. "
            "Examples: `de-CH`, `fr-CH`, `fr-FR`. This biases the results rather "
            "than restricting them — sources from other regions can still "
            "appear. If left blank, the deployment default set in the "
            "environment variable `BING_AGENT_DEFAULT_MARKET` applies. If left "
            "blank and the environment variable is not set, Bing may favour the "
            "region where the underlying Microsoft Foundry resource is deployed."
        ),
    )
    search_freshness: BingFreshnessPreset | None = Field(
        default=None,
        title="Only results published recently",
        description=(
            "Drops anything Bing discovered before a cut-off, counted back from "
            "each search. Unlike the region, this really does filter, and it "
            "applies to **every** search in the space — set it only for news "
            "spaces, since elsewhere it hides older pages that are still "
            "correct. "
            f"[Accepted `freshness` values]({_BING_QUERY_PARAMS_DOCS_URL}#freshness)"
        ),
    )

    # Burned config keys — never reintroduce a Bing field under one of these.
    #
    # 2026.36 briefly shipped `market` / `freshness` / `setLang` holding
    # ExposableParam `{expose, value}` objects, and spaces saved then still carry
    # that shape. A scalar field reusing one of these names would meet a dict at
    # validation, and an invalid tool config silently disables the whole tool.
    _BURNED_CONFIG_KEYS: ClassVar[frozenset[str]] = frozenset(
        {"market", "freshness", "setLang"},
    )

    @field_validator("search_market", "search_freshness", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: Any) -> Any:
        """Read a control cleared to ``""`` as unset, not a vocabulary error."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Keep the optional grounding knobs to one control each in the admin form."""
        schema = handler(core_schema)
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            return schema

        market = properties.get("searchMarket")
        if isinstance(market, dict):
            properties["searchMarket"] = _single_dropdown(
                market,
                values=get_args(BingMarket),
                blank_title="Not set",
            )

        freshness = properties.get("searchFreshness")
        if isinstance(freshness, dict):
            properties["searchFreshness"] = _single_dropdown(
                freshness,
                values=get_args(BingFreshnessPreset),
                blank_title="Not set",
                titles=_FRESHNESS_PRESET_TITLES,
            )

        return schema


BingAgentSearchRequest = BingAgentConfig.request_model()


__all__ = [
    "BingAgentConfig",
    "BingAgentSearchRequest",
    "BingFreshnessPreset",
    "BingMarket",
]
