from __future__ import annotations

from typing import Literal

from pydantic import Field

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings
from unique_search_proxy_client.web.settings.providers.base import (
    ProviderCredentials,
    provider_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr

_ENV_PREFIX = "VERTEXAI_AGENT_"

VertexAICredentialType = Literal["workload_identity", "service_account"]


@helm_settings(title="VertexAI Agent", helm_key="vertexaiAgent", egress=None)
@provider_credentials(_ENV_PREFIX)
class _VertexAIAgentCredentials(ProviderCredentials):
    """Environment-backed credentials for Vertex AI grounding (Google GenAI).

    Defaults to GCP workload identity (Application Default Credentials). The
    explicit ``service_account`` path stays available as a fallback, primarily
    for local development where workload identity is not available.
    """

    credential_type: VertexAICredentialType = Field(default="workload_identity")
    service_account_credentials: LogSecretStr | None = Field(default=None)
    service_account_scopes: list[str] = Field(
        default=["https://www.googleapis.com/auth/cloud-platform"],
    )


def _get_vertexai_agent_credentials() -> _VertexAIAgentCredentials:
    return get_settings(_VertexAIAgentCredentials, env_prefix=_ENV_PREFIX)


vertexai_agent_credentials = _get_vertexai_agent_credentials()

__all__ = ["vertexai_agent_credentials"]
