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

_DEFAULT_GOOGLE_API_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
_ENV_PREFIX = "GOOGLE_SEARCH_"


@helm_settings(title="Google Search", helm_key="googleSearch")
@provider_credentials(_ENV_PREFIX)
class _GoogleCredentials(ProviderCredentials):
    """Environment-backed credentials for Google Custom Search."""

    api_key: LogSecretStr = Field(default=LogSecretStr(NOT_PROVIDED))
    api_endpoint: str = Field(default=_DEFAULT_GOOGLE_API_ENDPOINT)
    engine_id: str = Field(default=NOT_PROVIDED)


def _get_google_search_credentials() -> _GoogleCredentials:
    return get_settings(_GoogleCredentials, env_prefix=_ENV_PREFIX)


google_search_credentials = _get_google_search_credentials()
