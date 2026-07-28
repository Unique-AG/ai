from __future__ import annotations

from typing import Annotated, ClassVar, Literal

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.agent_engines.base import (
    AgentEngineType,
    BaseAgentEngineConfig,
)


class BingAgentConfig(BaseAgentEngineConfig[Literal[AgentEngineType.BING]]):
    """Deployment + request defaults for Bing grounding via Azure AI Projects."""

    _request_model_name: ClassVar[str] = "BingAgentSearchRequest"

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
    agent_id: str | None = Field(
        default=None,
        description=(
            "Foundry agent name/id. Resolved from deployment env when not set. "
            "When empty, the service auto-provisions or looks up a grounding agent."
        ),
    )


BingAgentSearchRequest = BingAgentConfig.request_model()


__all__ = ["BingAgentConfig", "BingAgentSearchRequest"]
