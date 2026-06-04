import logging
from typing import Literal

from unique_search_proxy_core.crawlers import (
    BasicCrawlerConfig as BasicCrawlerProxyCoreConfig,
)
from unique_search_proxy_core.crawlers.base import CrawlerType as ProxyCrawlerType
from unique_search_proxy_sdk import UniqueSearchProxyClient
from unique_search_proxy_sdk._generated.models.crawl_url_result import CrawlUrlResult
from unique_search_proxy_sdk._generated.models.per_url_error import PerUrlError

from unique_web_search.client_settings import get_search_proxy_settings
from unique_web_search.services.crawlers.base import BaseCrawlerConfig, CrawlerType

_LOGGER = logging.getLogger(__name__)


class BasicCrawlerProxyConfig(
    BaseCrawlerConfig[CrawlerType.BASIC_PROXY], BasicCrawlerProxyCoreConfig
):
    crawler_type: Literal[CrawlerType.BASIC_PROXY] = CrawlerType.BASIC_PROXY


class BasicProxyCrawler:
    """Crawler that delegates fetching to the remote Unique Search Proxy service.

    Intermediate transition crawler: instead of fetching URLs in-process (see
    :class:`BasicCrawler`), it forwards the request to the search-proxy service
    via :class:`UniqueSearchProxyClient` and maps the per-URL results back to the
    markdown list contract shared by the other crawlers.
    """

    def __init__(self, config: BasicCrawlerProxyConfig):
        self.config: BasicCrawlerProxyConfig = config

    async def crawl(self, urls: list[str]) -> list[str]:
        return await self._crawl(urls)

    async def _crawl(self, urls: list[str]) -> list[str]:
        base_url = get_search_proxy_settings().base_url
        assert base_url is not None, "Unique Search Proxy base URL is not configured"

        try:
            async with UniqueSearchProxyClient(
                base_url=base_url,
                timeout=float(self.config.timeout),
            ) as client:
                response = await client.crawl.crawl(
                    urls,
                    crawler_type=ProxyCrawlerType.BASIC,
                    content_types=self.config.content_types,
                    timeout=self.config.timeout,
                    max_concurrent_requests=self.config.max_concurrent_requests,
                )
        except Exception as error:
            _LOGGER.exception("Unique Search Proxy crawl request failed")
            return [f"Unable to crawl URL via search proxy: {error}" for _ in urls]

        url_to_markdown = {
            result.url: _result_to_markdown(result) for result in response.results
        }

        return [
            url_to_markdown.get(url, "Error: URL not found in search proxy response")
            for url in urls
        ]


def _result_to_markdown(result: CrawlUrlResult) -> str:
    if isinstance(result.content, str):
        return result.content

    if isinstance(result.error, PerUrlError):
        return f"Error: {result.error.message}"

    if isinstance(result.raw, str):
        return result.raw

    return "Error: No content returned by search proxy"
