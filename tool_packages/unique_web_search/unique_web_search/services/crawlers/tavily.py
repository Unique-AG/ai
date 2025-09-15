import asyncio
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

        # Tavily only supports up to 20 URLs per request, so we need to batch the requests
        response = {"results": [], "failed_results": []}
        batch_size = 20

        async def process_batch(batch_urls: list[str]) -> dict:
            batch_response = await client.extract(
                urls=batch_urls,
                format="markdown",
                include_images=False,
                extract_depth=self.config.depth,
                timeout=self.config.timeout,
                include_favicon=False,
            )
            return batch_response

        tasks = [
            process_batch(urls[i : i + batch_size])
            for i in range(0, len(urls), batch_size)
        ]
        results = await asyncio.gather(*tasks)

        for result in results:
            response["results"].extend(result.get("results", []))
            response["failed_results"].extend(result.get("failed_results", []))

        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i : i + batch_size]
            batch_response = await client.extract(
                urls=batch_urls,
                format="markdown",
                include_images=False,
                extract_depth=self.config.depth,
                timeout=self.config.timeout,
                include_favicon=False,
            )
            response["results"].extend(batch_response.get("results", []))
            response["failed_results"].extend(batch_response.get("failed_results", []))

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
