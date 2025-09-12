from typing import Literal

from tavily import AsyncTavilyClient

from unique_web_search.client_settings import get_tavily_search_settings
from unique_web_search.services.crawlers.base import (
    BaseCrawler,
    BaseCrawlerConfig,
    CrawlerType,
)


class TavilyCrawlerConfig(BaseCrawlerConfig[CrawlerType.TAVILY]):
    crawler_type: Literal[CrawlerType.TAVILY] = CrawlerType.TAVILY
    depth: Literal["basic", "advanced"] = "advanced"


class TavilyCrawler(BaseCrawler[TavilyCrawlerConfig]):
    def __init__(self, config: TavilyCrawlerConfig):
        super().__init__(config)

    # TODO: find a tracking solution
    # @track(
    #     tags=["tavily", "scrape"],
    # )
    async def crawl(self, urls: list[str]) -> list[str]:
        api_key = get_tavily_search_settings().api_key
        assert api_key is not None

        client = AsyncTavilyClient(api_key=api_key)

        response = await client.extract(
            urls=urls,
            format="markdown",
            include_images=False,
            extract_depth=self.config.depth,
            timeout=self.config.timeout,
            include_favicon=False,
        )

        # Create a mapping from URL to content
        url_to_content = {}

        # Process successful results
        for result in response["results"]:
            url_to_content[result["url"]] = result["raw_content"]

        # Process failed results with error messages
        for failed_result in response["failed_results"]:
            url_to_content[failed_result["url"]] = f"Error: {failed_result['error']}"

        # Return results in the same order as input URLs, with fallback for missing URLs
        return [
            url_to_content.get(url, "Error: URL not found in response") for url in urls
        ]
