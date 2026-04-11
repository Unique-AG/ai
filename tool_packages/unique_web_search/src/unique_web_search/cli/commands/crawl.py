"""Crawl command: fetch full page content for a list of URLs."""

from __future__ import annotations

import asyncio
import logging

from unique_web_search.cli.formatting import (
    format_crawl_results,
    format_crawl_results_json,
)
from unique_web_search.services.crawlers import CrawlerConfigTypes, get_crawler_service

_LOGGER = logging.getLogger(__name__)

DEFAULT_PARALLEL = 10


async def _crawl_batch(
    crawler_config: CrawlerConfigTypes,
    urls: list[str],
) -> list[str]:
    crawler = get_crawler_service(crawler_config)
    return await crawler.crawl(urls)


async def _crawl_with_parallelism(
    crawler_config: CrawlerConfigTypes,
    urls: list[str],
    parallel: int,
) -> list[tuple[str, str, str | None]]:
    """Crawl URLs in batches of *parallel*, returning (url, content, error) triples."""
    results: list[tuple[str, str, str | None]] = []
    for i in range(0, len(urls), parallel):
        batch = urls[i : i + parallel]
        _LOGGER.info("Crawling batch %d–%d of %d", i + 1, i + len(batch), len(urls))
        try:
            contents = await _crawl_batch(crawler_config, batch)
            for url, content in zip(batch, contents):
                results.append((url, content, None))
        except Exception as e:
            _LOGGER.warning("Batch %d–%d failed: %s", i + 1, i + len(batch), e)
            for url in batch:
                results.append((url, "", str(e)))
    return results


def cmd_crawl(
    crawler_config: CrawlerConfigTypes,
    urls: list[str],
    parallel: int = DEFAULT_PARALLEL,
    output_json: bool = False,
) -> str:
    """Crawl a list of URLs and return their page content.

    Args:
        crawler_config: Validated crawler config.
        urls: URLs to crawl.
        parallel: How many URLs to crawl concurrently per batch.
        output_json: Return results as JSON.

    Returns:
        Formatted string of crawl results for terminal display.
    """
    results = asyncio.run(_crawl_with_parallelism(crawler_config, urls, parallel))

    if output_json:
        return format_crawl_results_json(results)
    return format_crawl_results(results)
