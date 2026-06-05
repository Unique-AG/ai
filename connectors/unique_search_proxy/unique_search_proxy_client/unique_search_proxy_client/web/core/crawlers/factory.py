from __future__ import annotations

from typing import TYPE_CHECKING, Any

from unique_search_proxy_core.crawlers.base import BaseCrawler

from unique_search_proxy_client.web.core.registry import get_crawler

if TYPE_CHECKING:
    from httpx import AsyncClient


def get_crawler_service(
    crawler_id: str,
    *,
    http_client: AsyncClient | None = None,
) -> BaseCrawler[Any]:
    """Instantiate a crawler by registered id."""
    crawler_cls = get_crawler(crawler_id)
    return crawler_cls(http_client=http_client)


__all__ = ["get_crawler_service"]
