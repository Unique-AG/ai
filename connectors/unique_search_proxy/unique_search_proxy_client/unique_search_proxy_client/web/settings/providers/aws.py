from __future__ import annotations

from pydantic import Field

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings
from unique_search_proxy_client.web.settings.providers.base import (
    ProviderCredentials,
    provider_credentials,
)

_DEFAULT_REGION = "us-east-1"
_DEFAULT_API_ENDPOINT = f"https://bedrock-agentcore.{_DEFAULT_REGION}.amazonaws.com"
_ENV_PREFIX = "AWS_SEARCH_"


@helm_settings(title="AWS AgentCore Web Search", helm_key="awsSearch")
@provider_credentials(_ENV_PREFIX)
class _AwsSearchCredentials(ProviderCredentials):
    """AgentCore InvokeWebSearch region and endpoint; credentials come from the default AWS chain."""

    region: str = Field(
        default=_DEFAULT_REGION,
        min_length=1,
        description="AWS region for SigV4 and the AgentCore endpoint.",
    )
    api_endpoint: str = Field(
        default=_DEFAULT_API_ENDPOINT,
        description=(
            "AgentCore endpoint. Must be "
            "https://bedrock-agentcore.<region>.amazonaws.com for the region above, "
            "or a PrivateLink endpoint under amazonaws.com. Other hosts are refused."
        ),
    )


def _get_aws_search_credentials() -> _AwsSearchCredentials:
    return get_settings(_AwsSearchCredentials, env_prefix=_ENV_PREFIX)


aws_search_credentials = _get_aws_search_credentials()
