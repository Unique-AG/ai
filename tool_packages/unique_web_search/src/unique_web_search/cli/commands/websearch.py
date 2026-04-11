"""Web search command: query the configured search engine and optionally crawl results."""

from __future__ import annotations

import asyncio
import logging

from unique_web_search.cli.formatting import format_websearch_results
from unique_web_search.services.crawlers import CrawlerConfigTypes, get_crawler_service
from unique_web_search.services.search_engine import SearchEngineConfigTypes
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineType
from unique_web_search.services.search_engine.schema import WebSearchResult

_LOGGER = logging.getLogger(__name__)

UNSUPPORTED_CLI_ENGINES = {SearchEngineType.BING}


def _instantiate_engine(
    config: SearchEngineConfigTypes,
) -> SearchEngine:
    """Instantiate the search engine service from its config."""
    from unique_web_search.services.search_engine.brave import BraveSearch
    from unique_web_search.services.search_engine.custom_api import CustomAPI
    from unique_web_search.services.search_engine.firecrawl import FireCrawlSearch
    from unique_web_search.services.search_engine.google import GoogleSearch
    from unique_web_search.services.search_engine.jina import JinaSearch
    from unique_web_search.services.search_engine.tavily import TavilySearch
    from unique_web_search.services.search_engine.vertexai import VertexAI

    if config.search_engine_name in UNSUPPORTED_CLI_ENGINES:
        raise ValueError(
            f"{config.search_engine_name} is not supported in CLI mode "
            f"(requires server-side LanguageModelService)."
        )

    match config.search_engine_name:
        case SearchEngineType.GOOGLE:
            return GoogleSearch(config)
        case SearchEngineType.BRAVE:
            return BraveSearch(config)
        case SearchEngineType.TAVILY:
            return TavilySearch(config)
        case SearchEngineType.JINA:
            return JinaSearch(config)
        case SearchEngineType.FIRECRAWL:
            return FireCrawlSearch(config)
        case SearchEngineType.VERTEXAI:
            return VertexAI(config)
        case SearchEngineType.CUSTOM_API:
            return CustomAPI(config)
        case _:
            raise ValueError(f"Unsupported search engine: {config.search_engine_name}")


async def _run_search(
    engine: SearchEngine,
    query: str,
) -> list[WebSearchResult]:
    return await engine.search(query)


async def _run_crawl(
    crawler_config: CrawlerConfigTypes,
    urls: list[str],
) -> list[str]:
    crawler = get_crawler_service(crawler_config)
    return await crawler.crawl(urls)


def cmd_websearch(
    search_engine_config: SearchEngineConfigTypes,
    crawler_config: CrawlerConfigTypes,
    query: str,
    fetch_size: int | None = None,
    no_crawl: bool = False,
) -> str:
    """Execute a web search and optionally crawl the result pages.

    Args:
        search_engine_config: Validated search engine config (from env + JSON).
        crawler_config: Validated crawler config (from env + JSON).
        query: The search query string.
        fetch_size: Override fetch_size if provided via CLI flag.
        no_crawl: Skip crawling, return URLs + snippets only.

    Returns:
        Formatted string of results for terminal display.
    """
    if fetch_size is not None:
        search_engine_config.fetch_size = fetch_size

    engine = _instantiate_engine(search_engine_config)
    results = asyncio.run(_run_search(engine, query))

    if not results:
        return "No results found."

    crawled_contents: list[str] | None = None
    if not no_crawl and engine.requires_scraping:
        urls = [r.url for r in results]
        try:
            crawled_contents = asyncio.run(_run_crawl(crawler_config, urls))
        except Exception as e:
            _LOGGER.warning("Crawling failed, showing snippets only: %s", e)

    return format_websearch_results(results, crawled_contents)
