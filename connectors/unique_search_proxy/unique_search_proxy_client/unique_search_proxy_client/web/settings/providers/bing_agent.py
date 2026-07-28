from __future__ import annotations

from pydantic import Field

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings
from unique_search_proxy_client.web.settings.providers.base import (
    ProviderCredentials,
    provider_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import (
    NOT_PROVIDED,
    LogSecretStr,
)

_ENV_PREFIX = "BING_AGENT_"


@helm_settings(title="Bing Agent", helm_key="bingAgent", egress=None)
@provider_credentials(_ENV_PREFIX)
class _BingAgentCredentials(ProviderCredentials):
    """Environment-backed credentials for Bing grounding via Azure AI Projects."""

    endpoint: LogSecretStr = Field(default=LogSecretStr(NOT_PROVIDED))
    bing_resource_connection_string: LogSecretStr = Field(
        default=LogSecretStr(NOT_PROVIDED),
    )
    agent_id: str | None = Field(default=None)
    bing_agent_model: LogSecretStr = Field(default=LogSecretStr(NOT_PROVIDED))
    azure_identity_credential_type: str = Field(default="default")
    azure_identity_validate_token_url: str = Field(
        default="https://management.azure.com/.default",
    )
    use_private_endpoint_transport: bool = Field(default=False)
    cleanup_on_start: bool = Field(
        default=False,
        description=(
            "If true, on process start delete Foundry agents whose names start with "
            "unique-grounding-with-bing- (auto-provisioned hash agents)."
        ),
    )


def _get_bing_agent_credentials() -> _BingAgentCredentials:
    return get_settings(_BingAgentCredentials, env_prefix=_ENV_PREFIX)


bing_agent_credentials = _get_bing_agent_credentials()

__all__ = ["bing_agent_credentials"]
