from typing import Literal, override

from firecrawl import AsyncFirecrawl

from unique_web_search.client_settings import (
    get_firecrawl_search_settings,
)
from unique_web_search.services.crawlers.base import (
    BaseCrawler,
    BaseCrawlerConfigExperimental,
    CrawlerType,
)
from unique_web_search.services.crawlers.url_safety import ResolvedCrawlTarget
from unique_web_search.services.proxy.bridge import (
    open_search_proxy_client,
)
from unique_web_search.services.proxy.mappers import map_crawl_response


class FirecrawlCrawlerConfig(BaseCrawlerConfigExperimental[CrawlerType.FIRECRAWL]):
    crawler_type: Literal[CrawlerType.FIRECRAWL] = CrawlerType.FIRECRAWL


class FirecrawlCrawler(BaseCrawler[FirecrawlCrawlerConfig]):
    supports_proxy_crawl = True

    def __init__(self, config: FirecrawlCrawlerConfig):
        super().__init__(config)

    # TODO: Find a solution for tracking
    # @track(
    #     tags=["firecrawl", "scrape"],
    # )
    @override
    async def _proxy_crawl(self, urls: list[str]) -> list[str]:
        async with open_search_proxy_client(
            timeout=float(self.config.timeout),
        ) as client:
            response = await client.crawl.firecrawl(
                urls=urls,
                timeout=int(self.config.timeout),
                only_main_content=True,
            )
            return map_crawl_response(response, urls)

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
