from __future__ import annotations

from typing import Annotated, ClassVar, Literal

from pydantic import Field, field_validator
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.agent_engines.base import (
    AgentEngineType,
    BaseAgentEngineConfig,
)
from unique_search_proxy_core.agent_engines.vertexai.settings import (
    resolve_enable_enterprise_search,
    vertex_ai_env_settings,
)


def _get_force_activate_enterprise_search_description() -> str:
    if vertex_ai_env_settings.force_activate_enterprise_search:
        return "This parameter has been enforced by infra team."

    return (
        "When true, ground answers with Vertex AI Enterprise Web Search "
        "(Agent Platform Search, SEC4-compliant)"
    )


def _enterprise_search_rjsf_tag() -> RJSFMetaTag:
    return RJSFMetaTag.BooleanWidget.checkbox(
        title="Enable Enterprise Search",
        help=_get_force_activate_enterprise_search_description(),
        disabled=vertex_ai_env_settings.force_activate_enterprise_search,
    )


EnableEnterpriseSearch = Annotated[bool, _enterprise_search_rjsf_tag()]


class VertexAIAgentConfig(BaseAgentEngineConfig[Literal[AgentEngineType.VERTEXAI]]):
    """Deployment + request defaults for Vertex AI grounding (Google GenAI)."""

    _request_model_name: ClassVar[str] = "VertexAIAgentSearchRequest"
    _exposed_params_model_name: ClassVar[str] = "VertexAIAgentExposedParams"

    engine: Annotated[
        Literal[AgentEngineType.VERTEXAI], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=AgentEngineType.VERTEXAI,
        title="Agent engine",
        description="Provider discriminator; must be `vertexai` for this config.",
    )
    vertexai_model_name: str = Field(
        default=vertex_ai_env_settings.default_vertex_ai_model_name,
        description="Gemini model name for grounded generation",
    )
    enable_enterprise_search: EnableEnterpriseSearch = Field(
        default=vertex_ai_env_settings.force_activate_enterprise_search,
        validate_default=True,
    )

    @field_validator("enable_enterprise_search", mode="before")
    @classmethod
    def validate_enable_enterprise_search(cls, v: object) -> bool:
        """Pin the value on when infra forces enterprise search for ZDR tenants."""
        return resolve_enable_enterprise_search(bool(v) if v is not None else False)


VertexAIAgentSearchRequest = VertexAIAgentConfig.request_model()


__all__ = [
    "VertexAIAgentConfig",
    "VertexAIAgentSearchRequest",
]
