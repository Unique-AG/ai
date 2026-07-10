from __future__ import annotations

from typing import Annotated, ClassVar, Literal

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.agent_engines.base import (
    AgentEngineType,
    BaseAgentEngineConfig,
)


class VertexAIAgentConfig(BaseAgentEngineConfig[Literal[AgentEngineType.VERTEXAI]]):
    """Deployment + request defaults for Vertex AI grounding (Google GenAI)."""

    _request_model_name: ClassVar[str] = "VertexAIAgentSearchRequest"

    engine: Annotated[
        Literal[AgentEngineType.VERTEXAI], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=AgentEngineType.VERTEXAI,
        title="Agent engine",
        description="Provider discriminator; must be `vertexai` for this config.",
    )
    vertexai_model_name: str = Field(
        default="gemini-3-flash-preview",
        description="Gemini model name for grounded generation",
    )
    enable_enterprise_search: bool = Field(
        default=False,
        description="Use enterprise web search grounding tool instead of Google Search",
    )


VertexAIAgentSearchRequest = VertexAIAgentConfig.request_model()


__all__ = [
    "VertexAIAgentConfig",
    "VertexAIAgentSearchRequest",
]
