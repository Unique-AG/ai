from __future__ import annotations

from typing import Literal

from pydantic import Field

from unique_search_proxy_client.web.settings.base import get_settings
from unique_search_proxy_client.web.settings.providers.base import (
    NOT_PROVIDED,
    ProviderCredentials,
    provider_credentials,
)
from unique_search_proxy_client.web.utils.url import join_url_path

_FIRECRAWL_API_BASE = "https://api.firecrawl.dev"
FirecrawlApiVersion = Literal["v2"]
_DEFAULT_FIRECRAWL_API_VERSION: FirecrawlApiVersion = "v2"
FirecrawlOperation = Literal["batch_scrape", "search"]
_FIRECRAWL_OPERATION_PATHS: dict[FirecrawlOperation, tuple[str, ...]] = {
    "batch_scrape": ("batch", "scrape"),
    "search": ("search",),
}
_ENV_PREFIX = "FIRECRAWL_"


@provider_credentials(_ENV_PREFIX)
class _FirecrawlCredentials(ProviderCredentials):
    """Environment-backed credentials for Firecrawl v2 APIs."""

    api_key: str = Field(default=NOT_PROVIDED)
    api_endpoint: str = Field(default=_FIRECRAWL_API_BASE)
    api_version: FirecrawlApiVersion = Field(default=_DEFAULT_FIRECRAWL_API_VERSION)

    def _versioned_base(self) -> str:
        return join_url_path(self.api_endpoint, self.api_version)

    def _endpoint(self, operation: FirecrawlOperation) -> str:
        return join_url_path(
            self._versioned_base(), *_FIRECRAWL_OPERATION_PATHS[operation]
        )

    @property
    def batch_scrape_endpoint(self) -> str:
        return self._endpoint("batch_scrape")

    @property
    def search_endpoint(self) -> str:
        return self._endpoint("search")


def _get_firecrawl_crawl_credentials() -> _FirecrawlCredentials:
    return get_settings(_FirecrawlCredentials, env_prefix=_ENV_PREFIX)


firecrawl_crawl_credentials = _get_firecrawl_crawl_credentials()
