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
    market: BingMarket | None = Field(
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
    freshness: BingFreshnessPreset | None = Field(
        default=None,
        title="Only results published recently",
        description=(
            "Only includes results Bing discovered within the chosen timeframe, "
            "counted back from each search. This is a hard filter and it applies "
            "to every search in the space."
        ),
    )

    # Spaces saved on 2026.36 hold an ExposableParam `{expose, value}` object
    # under `market` and `freshness`, where these fields now expect a scalar.
    # node-chat data migration `20260908120000_drop_bing_grounding_exposable_params`
    # deletes those keys; the validator below reads the same shape as unset for
    # any row the migration has not reached, because an invalid tool config
    # silently disables the whole tool instead of reporting the problem.
    @field_validator("market", "freshness", mode="before")
    @classmethod
    def _coerce_unset(cls, value: Any) -> Any:
        """Read a cleared control, or a retired `{expose, value}` object, as unset."""
        if isinstance(value, Mapping):
            return None
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

        market = properties.get("market")
        if isinstance(market, dict):
            properties["market"] = _single_dropdown(
                market,
                values=get_args(BingMarket),
                blank_title="Not set",
            )

        freshness = properties.get("freshness")
        if isinstance(freshness, dict):
            properties["freshness"] = _single_dropdown(
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
