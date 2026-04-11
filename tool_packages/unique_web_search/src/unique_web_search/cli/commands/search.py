"""Search command: query the configured search engine and return URLs with snippets."""

from __future__ import annotations

import asyncio
import logging

from unique_web_search.cli.formatting import (
    format_search_results,
    format_search_results_json,
)
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


def cmd_search(
    search_engine_config: SearchEngineConfigTypes,
    query: str,
    fetch_size: int | None = None,
    output_json: bool = False,
) -> str:
    """Execute a web search and return URLs with snippets.

    Args:
        search_engine_config: Validated search engine config (from env + JSON).
        query: The search query string.
        fetch_size: Override fetch_size if provided via CLI flag.
        output_json: Return results as JSON.

    Returns:
        Formatted string of results for terminal display.
    """
    if fetch_size is not None:
        search_engine_config.fetch_size = fetch_size

    engine = _instantiate_engine(search_engine_config)
    results = asyncio.run(_run_search(engine, query))

    if not results:
        if output_json:
            return "[]"
        return "No results found."

    if output_json:
        return format_search_results_json(results)
    return format_search_results(results)
