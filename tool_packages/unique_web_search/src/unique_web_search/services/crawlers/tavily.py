import asyncio

from tavily import AsyncTavilyClient
from typing_extensions import override
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.tavily.schema import TavilyConfig

from unique_web_search.client_settings import get_tavily_search_settings
from unique_web_search.services.crawlers.base import BaseCrawler
from unique_web_search.services.crawlers.registry import register_crawler
from unique_web_search.services.crawlers.url_safety import ResolvedCrawlTarget


@register_crawler(
    name="tavily",
    key=CrawlerType.TAVILY,
    config_cls=TavilyConfig,
    config_display_name="Tavily",
)
class TavilyCrawler(BaseCrawler[TavilyConfig]):
    def __init__(self, config: TavilyConfig):
        super().__init__(config)

    @override
    async def _legacy_crawl(self, targets: list[ResolvedCrawlTarget]) -> list[str]:
        urls = [target.normalized_url for target in targets]

        api_key = get_tavily_search_settings().api_key
        assert api_key is not None, "Tavily API key is not configured"

        client = AsyncTavilyClient(api_key=api_key)

        # Tavily only supports up to 20 URLs per request, so we need to batch the requests
        response = {"results": [], "failed_results": []}
        batch_size = 20

        async def process_batch(batch_urls: list[str]) -> dict:
            batch_response = await client.extract(
                urls=batch_urls,
                format=self.config.format,
                include_images=self.config.include_images,
                extract_depth=self.config.extract_depth,
                timeout=self.config.timeout,
                include_favicon=self.config.include_favicon,
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
