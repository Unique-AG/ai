from __future__ import annotations

from typing import TYPE_CHECKING, Any

from unique_search_proxy.web.core.crawlers.base import BaseCrawler
from unique_search_proxy.web.core.crawlers.config_types import CrawlerConfigTypes
from unique_search_proxy.web.core.registry import get_crawler

if TYPE_CHECKING:
    from httpx import AsyncClient


def get_crawler_service(
    config: CrawlerConfigTypes,
    *,
    http_client: AsyncClient | None = None,
) -> BaseCrawler[Any]:
    """Instantiate a crawler from a validated discriminated config."""
    crawler_cls = get_crawler(config.crawler)
    return crawler_cls(config, http_client=http_client)
