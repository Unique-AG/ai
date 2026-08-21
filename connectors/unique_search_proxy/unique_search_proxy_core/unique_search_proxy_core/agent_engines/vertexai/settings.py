import os
import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PREFIX = "VERTEXAI_AGENT_"


class _VertexAIEnvSettings(BaseSettings):
    default_vertex_ai_model_name: str = Field(
        default="gemini-3-flash-preview",
        description="Default Vertex AI model name for grounded generation",
    )
    force_activate_enterprise_search: bool = Field(
        default=False,
        description=(
            "When true, pin Enable Enterprise Search on for ZDR tenants so the "
            "toggle cannot be turned off in config or at request time."
        ),
    )


def _get_settings() -> _VertexAIEnvSettings:
    if "pytest" in sys.modules:
        env_file = Path(os.getcwd()) / "tests/test.env"
    else:
        env_file = Path(os.getcwd()) / ".env"

    class _Settings(_VertexAIEnvSettings):
        model_config = SettingsConfigDict(
            env_file=env_file,
            env_prefix=_ENV_PREFIX,
            extra="ignore",
        )

    return _Settings()


vertex_ai_env_settings = _get_settings()


def resolve_enable_enterprise_search(value: bool | None = False) -> bool:
    """Return the effective enterprise-search flag after infra enforcement.

    ZDR tenants set ``VERTEXAI_AGENT_FORCE_ACTIVATE_ENTERPRISE_SEARCH=true`` so
    the cheaper standard grounding edition cannot be selected.
    """
    if vertex_ai_env_settings.force_activate_enterprise_search:
        return True
    return bool(value)
