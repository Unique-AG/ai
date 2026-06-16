from __future__ import annotations

from pydantic import Field

from unique_search_proxy_client.web.settings.base import get_settings
from unique_search_proxy_client.web.settings.providers.base import (
    NOT_PROVIDED,
    ProviderCredentials,
    provider_credentials,
)

_DEFAULT_BRAVE_API_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
_ENV_PREFIX = "BRAVE_SEARCH_"


@provider_credentials(_ENV_PREFIX)
class _BraveCredentials(ProviderCredentials):
    """Environment-backed credentials for Brave Web Search."""

    api_key: str = Field(default=NOT_PROVIDED)
    api_endpoint: str = Field(default=_DEFAULT_BRAVE_API_ENDPOINT)


def _get_brave_search_credentials() -> _BraveCredentials:
    return get_settings(_BraveCredentials, env_prefix=_ENV_PREFIX)


brave_search_credentials = _get_brave_search_credentials()
