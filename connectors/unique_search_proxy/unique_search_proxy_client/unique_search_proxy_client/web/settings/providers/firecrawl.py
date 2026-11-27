from __future__ import annotations

from typing import Literal

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
from unique_search_proxy_client.web.utils.url import join_url_path

_FIRECRAWL_API_BASE = "https://api.firecrawl.dev"
FirecrawlApiVersion = Literal["v2"]
_DEFAULT_FIRECRAWL_API_VERSION: FirecrawlApiVersion = "v2"
FirecrawlZeroDataRetention = Literal["none", "anon", "zdr"]
_ZERO_DATA_RETENTION_STRICTNESS: dict[str, int] = {"none": 0, "anon": 1, "zdr": 2}
FirecrawlOperation = Literal["batch_scrape", "scrape", "search"]
_FIRECRAWL_OPERATION_PATHS: dict[FirecrawlOperation, tuple[str, ...]] = {
    "batch_scrape": ("batch", "scrape"),
    "scrape": ("scrape",),
    "search": ("search",),
}
_ENV_PREFIX = "FIRECRAWL_"


@helm_settings(title="Firecrawl", helm_key="firecrawl")
@provider_credentials(_ENV_PREFIX)
class _FirecrawlCredentials(ProviderCredentials):
    """Environment-backed credentials for Firecrawl v2 APIs."""

    api_key: LogSecretStr = Field(default=LogSecretStr(NOT_PROVIDED))
    api_endpoint: str = Field(default=_FIRECRAWL_API_BASE)
    api_version: FirecrawlApiVersion = Field(default=_DEFAULT_FIRECRAWL_API_VERSION)
    zero_data_retention: FirecrawlZeroDataRetention = Field(
        default="none",
        description=(
            "Zero data retention for Firecrawl search and page reads. Searches "
            "send it as Firecrawl `enterprise`: `anon` is anonymized ZDR (2 "
            "credits per 10 results), `zdr` end-to-end ZDR (10 credits per 10 "
            "results), most likely the right choice in production. Page reads "
            "by the Firecrawl crawler have no anonymized mode, so both `anon` "
            "and `zdr` send `zeroDataRetention: true`, for 1 extra credit per "
            "page. The mode must be enabled for the Firecrawl team, otherwise "
            "every call fails. `none` sends nothing. A search or crawler "
            "configuration can raise the mode for its own calls but never "
            "lower it."
        ),
    )

    def search_enterprise_modes(self, requested: str = "deployment") -> list[str]:
        """Firecrawl ``enterprise`` value: the stricter of deployment and request."""
        mode = max(
            self.zero_data_retention,
            requested if requested in _ZERO_DATA_RETENTION_STRICTNESS else "none",
            key=_ZERO_DATA_RETENTION_STRICTNESS.__getitem__,
        )
        return [] if mode == "none" else [mode]

    def scrape_zero_data_retention(self, requested: bool = False) -> bool:
        """Whether a page read sends ``zeroDataRetention``: deployment or request."""
        return requested or self.zero_data_retention != "none"

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
    def scrape_endpoint(self) -> str:
        return self._endpoint("scrape")

    @property
    def search_endpoint(self) -> str:
        return self._endpoint("search")


def _get_firecrawl_crawl_credentials() -> _FirecrawlCredentials:
    return get_settings(_FirecrawlCredentials, env_prefix=_ENV_PREFIX)


firecrawl_crawl_credentials = _get_firecrawl_crawl_credentials()
