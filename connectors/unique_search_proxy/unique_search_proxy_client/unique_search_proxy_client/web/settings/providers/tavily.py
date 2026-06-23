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
from unique_search_proxy_client.web.utils.url import join_url_path

_TAVILY_API_BASE = "https://api.tavily.com"
TavilyOperation = Literal["extract", "search"]
_TAVILY_OPERATION_PATHS: dict[TavilyOperation, tuple[str, ...]] = {
    "extract": ("extract",),
    "search": ("search",),
}
_ENV_PREFIX = "TAVILY_"


@provider_credentials(_ENV_PREFIX)
class _TavilyCredentials(ProviderCredentials):
    """Environment-backed credentials for Tavily APIs."""

    api_key: LogSecretStr = Field(default=LogSecretStr(NOT_PROVIDED))
    api_endpoint: str = Field(default=_TAVILY_API_BASE)

    def _endpoint(self, operation: TavilyOperation) -> str:
        return join_url_path(self.api_endpoint, *_TAVILY_OPERATION_PATHS[operation])

    @property
    def extract_endpoint(self) -> str:
        return self._endpoint("extract")

    @property
    def search_endpoint(self) -> str:
        return self._endpoint("search")


def _get_tavily_crawl_credentials() -> _TavilyCredentials:
    return get_settings(_TavilyCredentials, env_prefix=_ENV_PREFIX)


tavily_crawl_credentials = _get_tavily_crawl_credentials()
