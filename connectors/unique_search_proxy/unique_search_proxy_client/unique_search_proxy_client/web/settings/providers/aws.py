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
    """Region and endpoint for AgentCore InvokeWebSearch.

    Credentials come from the default AWS chain: the projected OIDC token in
    a cluster, or a short-lived ``aws login`` session locally. There is no
    static key setting.
    """

    region: str = Field(
        default=_DEFAULT_REGION,
        min_length=1,
        description="AWS region for SigV4 and the AgentCore endpoint.",
    )
    api_endpoint: str = Field(
        default=_DEFAULT_API_ENDPOINT,
        description=(
            "AgentCore endpoint. Must be "
            "https://bedrock-agentcore.<region>.amazonaws.com for the region above."
        ),
    )


def _get_aws_search_credentials() -> _AwsSearchCredentials:
    return get_settings(_AwsSearchCredentials, env_prefix=_ENV_PREFIX)


aws_search_credentials = _get_aws_search_credentials()
