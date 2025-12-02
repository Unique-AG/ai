from httpx import AsyncClient, HTTPError
import logging
import asyncio
from core.schema import WebSearchResult, WebSearchResults

_LOGGER = logging.getLogger(__name__)


async def _resolve_url(client: AsyncClient, web_search_result: WebSearchResult):
    try:
        resp = await client.head(web_search_result.url, follow_redirects=True)
        web_search_result.url = str(resp.url)
        return web_search_result
    except HTTPError as e:
        _LOGGER.error(f"Unable to redirect URL: {web_search_result.url}: {e}")
        return web_search_result


async def resolve_all(web_search_results: WebSearchResults):
    async with AsyncClient(follow_redirects=True, timeout=10) as client:
        tasks = [_resolve_url(client, result) for result in web_search_results.results]
        results = await asyncio.gather(*tasks)
        return WebSearchResults(results=results)
