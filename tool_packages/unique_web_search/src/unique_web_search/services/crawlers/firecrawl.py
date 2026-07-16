from typing import override

from firecrawl import AsyncFirecrawl
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.firecrawl.schema import FirecrawlConfig

from unique_web_search.client_settings import (
    get_firecrawl_search_settings,
)
from unique_web_search.services.crawlers.base import BaseCrawler
from unique_web_search.services.crawlers.registry import register_crawler
from unique_web_search.services.crawlers.url_safety import ResolvedCrawlTarget


@register_crawler(
    name="firecrawl",
    key=CrawlerType.FIRECRAWL,
    config_cls=FirecrawlConfig,
    config_display_name="Firecrawl",
)
class FirecrawlCrawler(BaseCrawler[FirecrawlConfig]):
    @override
    async def _legacy_crawl(self, targets: list[ResolvedCrawlTarget]) -> list[str]:
        urls = [target.normalized_url for target in targets]

        api_key = get_firecrawl_search_settings().api_key
        assert api_key is not None, "Firecrawl API key is not configured"

        client = AsyncFirecrawl(api_key=api_key)

        response = await client.batch_scrape(
            urls=urls,
            formats=["markdown"],
            wait_timeout=self.config.timeout,
        )

        results = response.data

        markdowns = [
            result.markdown
            if result.markdown is not None
            else "An error occurred while scraping the URL"
            for result in results
        ]

        return markdowns
