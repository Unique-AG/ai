import logging
from time import time

from unique_web_search.services.crawlers import (
    CrawlerTypes,
)
from unique_web_search.services.search_engine import (
    SearchEngineTypes,
    WebSearchResult,
)

logger = logging.getLogger(f"PythonAssistantCoreBundle.{__name__}")


class SearchAndCrawlService:
    def __init__(
        self,
        search_engine_service: SearchEngineTypes,
        crawler_service: CrawlerTypes,
    ):
        self.search_engine_service = search_engine_service

        self.crawler_service = crawler_service

    async def search_and_crawl(
        self, query: str, **kwargs
    ) -> tuple[list[WebSearchResult], dict[str, float]]:
        if not self.search_engine_service.is_configured:
            raise ValueError(
                f"Search engine {self.search_engine_service.config.search_engine_name} is not configured."
                "Please check the configuration or reachout to IT support."
            )

        if (
            self.search_engine_service.requires_scraping
            and self.crawler_service is None
        ):
            raise ValueError(
                "Crawler service is required for search engine that requires scraping"
            )

        search_results, search_time = await self._search(query, **kwargs)

        crawl_time = 0
        if self.search_engine_service.requires_scraping:
            search_results, crawl_time = await self._crawl_and_update_content(
                search_results
            )

        time_info = {
            "search_time": search_time,
            "crawl_time": crawl_time,
            "total_time": search_time + crawl_time,
        }

        return search_results, time_info

    async def _search(
        self, query: str, **kwargs
    ) -> tuple[list[WebSearchResult], float]:
        try:
            start_time = time()
            search_results = await self.search_engine_service.search(query, **kwargs)
            end_time = time()
            delta_time = end_time - start_time
            logger.info(
                f"Search with {self.search_engine_service.config.search_engine_name} completed in {delta_time} seconds"
            )
            return search_results, delta_time
        except Exception as e:
            logger.error(f"Failed to execute search: {str(e)}")
            raise ValueError("Failed to execute search")

    async def _crawl_and_update_content(
        self, search_results: list[WebSearchResult]
    ) -> tuple[list[WebSearchResult], float]:
        try:
            start_time = time()
            markdown_results = await self.crawler_service.crawl(
                [result.url for result in search_results]
            )

            for result, markdown in zip(search_results, markdown_results):
                result.content = markdown

            delta_time = time() - start_time
            logger.info(
                f"Crawled {len(search_results)} pages with {self.crawler_service.config.crawler_type} completed in {delta_time} seconds"
            )
            return search_results, delta_time

        except Exception as e:
            logger.error(f"Failed to execute crawl: {str(e)}")
            raise ValueError("Failed to execute crawl")
