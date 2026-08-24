from __future__ import annotations

from typing import Annotated, ClassVar, Literal, TypeAlias

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.agent_engines.base import (
    AgentEngineType,
    BaseAgentEngineConfig,
)
from unique_search_proxy_core.param_policy.exposable_param import ExposableParam
from unique_search_proxy_core.schema import DeactivatedNone

#: Named recency windows accepted by the Bing ``freshness`` knob.
BingFreshnessPreset: TypeAlias = Literal["Day", "Week", "Month"]

StrOrNone: TypeAlias = Annotated[str, Field(title="String")] | DeactivatedNone
FreshnessOrNone: TypeAlias = (
    Annotated[BingFreshnessPreset, Field(title="Preset")]
    | Annotated[str, Field(title="Date range")]
    | DeactivatedNone
)

ExposableStrOrNone = ExposableParam[StrOrNone]
ExposableFreshness = ExposableParam[FreshnessOrNone]

_BING_QUERY_PARAMS_DOCS_URL = "https://learn.microsoft.com/bing/search-apis/bing-web-search/reference/query-parameters"


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
    market: ExposableStrOrNone = Field(
        default=ExposableStrOrNone(expose=False, value=None),
        title="Market",
        description=(
            "Market the results come from (Bing `mkt`), e.g. `en-US`, `fr-CH`. "
            "Bing infers it from the caller when unset."
        ),
    )
    set_lang: ExposableStrOrNone = Field(
        default=ExposableStrOrNone(expose=False, value=None),
        title="Interface language",
        description=(
            "Language for Bing user-interface strings (Bing `setLang`), e.g. `en`."
        ),
    )
    freshness: ExposableFreshness = Field(
        default=ExposableFreshness(expose=False, value=None),
        title="Freshness",
        description=(
            "Recency filter (Bing `freshness`): `Day`, `Week`, `Month`, or a "
            "`YYYY-MM-DD..YYYY-MM-DD` range. "
            f"[Accepted values]({_BING_QUERY_PARAMS_DOCS_URL})"
        ),
    )


BingAgentSearchRequest = BingAgentConfig.request_model()


__all__ = [
    "BingAgentConfig",
    "BingAgentSearchRequest",
    "BingFreshnessPreset",
    "ExposableFreshness",
    "ExposableStrOrNone",
]
