from __future__ import annotations

from pydantic import Field

from unique_search_proxy_client.web.settings.base import get_settings
from unique_search_proxy_client.web.settings.providers.base import (
    ProviderCredentials,
    provider_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr

_ENV_PREFIX = "VERTEXAI_AGENT_"


@provider_credentials(_ENV_PREFIX)
class _VertexAIAgentCredentials(ProviderCredentials):
    """Environment-backed credentials for Vertex AI grounding (Google GenAI)."""

    service_account_credentials: LogSecretStr | None = Field(default=None)
    service_account_scopes: list[str] | None = Field(default=None)


def _get_vertexai_agent_credentials() -> _VertexAIAgentCredentials:
    return get_settings(_VertexAIAgentCredentials, env_prefix=_ENV_PREFIX)


vertexai_agent_credentials = _get_vertexai_agent_credentials()

__all__ = ["vertexai_agent_credentials"]
