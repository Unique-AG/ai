from typing import Literal

from firecrawl import AsyncFirecrawl

from unique_web_search.client_settings import (
    get_firecrawl_search_settings,
)
from unique_web_search.services.crawlers.base import (
    BaseCrawler,
    BaseCrawlerConfigExperimental,
    CrawlerType,
)


class FirecrawlCrawlerConfig(BaseCrawlerConfigExperimental[CrawlerType.FIRECRAWL]):
    crawler_type: Literal[CrawlerType.FIRECRAWL] = CrawlerType.FIRECRAWL


class FirecrawlCrawler(BaseCrawler[FirecrawlCrawlerConfig]):
    def __init__(self, config: FirecrawlCrawlerConfig):
        super().__init__(config)

    # TODO: Find a solution for tracking
    # @track(
    #     tags=["firecrawl", "scrape"],
    # )
    async def crawl(self, urls: list[str]) -> list[str]:
        api_key = get_firecrawl_search_settings().api_key
        assert api_key is not None

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
