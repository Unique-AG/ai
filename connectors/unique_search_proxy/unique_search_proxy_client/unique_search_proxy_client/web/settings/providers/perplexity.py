from __future__ import annotations

from pydantic import Field

from unique_search_proxy_client.web.settings.base import get_settings
from unique_search_proxy_client.web.settings.providers.base import (
    NOT_PROVIDED,
    ProviderCredentials,
    provider_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr

_DEFAULT_PERPLEXITY_API_ENDPOINT = "https://api.perplexity.ai/search"
_ENV_PREFIX = "PERPLEXITY_SEARCH_"


@provider_credentials(_ENV_PREFIX)
class _PerplexityCredentials(ProviderCredentials):
    """Environment-backed credentials for Perplexity Search."""

    api_key: LogSecretStr = Field(default=LogSecretStr(NOT_PROVIDED))
    api_endpoint: str = Field(default=_DEFAULT_PERPLEXITY_API_ENDPOINT)


def _get_perplexity_search_credentials() -> _PerplexityCredentials:
    return get_settings(_PerplexityCredentials, env_prefix=_ENV_PREFIX)


perplexity_search_credentials = _get_perplexity_search_credentials()
