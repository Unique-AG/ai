from __future__ import annotations

from typing import Literal

from pydantic import Field

from unique_search_proxy_client.web.settings.base import get_settings
from unique_search_proxy_client.web.settings.providers.base import (
    NOT_PROVIDED,
    ProviderCredentials,
    provider_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr

_JINA_DOMAIN = "jina.ai"
_JINA_SUBDOMAINS: dict[str, dict[str, str]] = {
    "global": {"read": "r", "search": "s"},
    "eu-beta": {"read": "eu-r-beta", "search": "eu-s-beta"},
}
JinaDeployment = Literal["global", "eu-beta"]
_DEFAULT_JINA_DEPLOYMENT: JinaDeployment = "global"
_ENV_PREFIX = "JINA_"


@provider_credentials(_ENV_PREFIX)
class _JinaCredentials(ProviderCredentials):
    """Environment-backed credentials for Jina Reader and Search."""

    api_key: LogSecretStr = Field(default=LogSecretStr(NOT_PROVIDED))
    deployment: JinaDeployment = Field(default=_DEFAULT_JINA_DEPLOYMENT)
    api_domain: str = Field(default=_JINA_DOMAIN)

    def _endpoint(self, operation: Literal["read", "search"]) -> str:
        subdomain = _JINA_SUBDOMAINS[self.deployment][operation]
        return f"https://{subdomain}.{self.api_domain}/"

    @property
    def reader_endpoint(self) -> str:
        return self._endpoint("read")

    @property
    def search_endpoint(self) -> str:
        return self._endpoint("search")


def _get_jina_crawl_credentials() -> _JinaCredentials:
    return get_settings(_JinaCredentials, env_prefix=_ENV_PREFIX)


jina_crawl_credentials = _get_jina_crawl_credentials()
