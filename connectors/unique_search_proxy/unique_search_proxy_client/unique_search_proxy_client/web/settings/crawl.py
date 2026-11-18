from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings

CRAWL_ENV_PREFIX = "CRAWL_"


@helm_settings(
    title="Crawl",
    helm_key="crawl",
    kind="internal",
    gated=False,
    egress=None,
    env_prefix=CRAWL_ENV_PREFIX,
)
class CrawlSettings(BaseSettings):
    """Whether the proxy may fetch websites."""

    model_config = SettingsConfigDict(
        env_prefix=CRAWL_ENV_PREFIX,
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        description="When false, POST /v1/crawl returns 503 and fetches nothing.",
    )


def get_crawl_settings() -> CrawlSettings:
    return get_settings(CrawlSettings, env_prefix=CRAWL_ENV_PREFIX)


def crawl_enabled() -> bool:
    return get_crawl_settings().enabled


crawl_settings = get_crawl_settings()
