"""Search command: query the configured search engine and return URLs with snippets."""

from __future__ import annotations

import asyncio
import logging
from typing import cast

from unique_web_search.cli.formatting import (
    format_search_results,
    format_search_results_json,
)
from unique_web_search.services.search_engine import (
    SearchEngineConfigTypes,
    get_search_engine_service,
)
from unique_web_search.services.search_engine.base import SearchEngine, SearchEngineType
from unique_web_search.services.search_engine.schema import WebSearchResult

_LOGGER = logging.getLogger(__name__)

UNSUPPORTED_CLI_ENGINES = {SearchEngineType.BING}


def _instantiate_engine(
    config: SearchEngineConfigTypes,
) -> SearchEngine:
    """Instantiate the search engine, reusing the shared factory."""
    if config.search_engine_name in UNSUPPORTED_CLI_ENGINES:
        raise ValueError(
            f"{config.search_engine_name} is not supported in CLI mode "
            f"(requires server-side LanguageModelService)."
        )
    return cast(
        SearchEngine,
        get_search_engine_service(config, None),  # type: ignore[arg-type]
    )


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
