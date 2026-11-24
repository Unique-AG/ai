from __future__ import annotations

import asyncio
from logging import getLogger
from time import monotonic

import httpx
from unique_search_proxy_core.context import SERVICE_ID_HEADER
from unique_search_proxy_sdk._generated.api.configuration import (
    list_providers_v1_configuration_providers_get as list_providers,
)
from unique_search_proxy_sdk._generated.client import Client
from unique_search_proxy_sdk._generated.models.providers_list_response import (
    ProvidersListResponse,
)
from unique_search_proxy_sdk._generated.types import UNSET

_LOGGER = getLogger(__name__)

_CACHE_SECONDS = 60.0
_TIMEOUT_SECONDS = 2.0

_cached: tuple[float, bool] | None = None
_refresh: tuple[asyncio.AbstractEventLoop, asyncio.Task[None]] | None = None


def crawling_enabled() -> bool:
    """Whether the search proxy accepts crawl requests (its ``CRAWL_ENABLED``)."""
    global _cached
    from unique_web_search.settings import env_settings

    base_url = env_settings.search_proxy_base_url
    if base_url is None:
        return True
    if _cached is not None:
        if monotonic() - _cached[0] < _CACHE_SECONDS:
            return _cached[1]
        # On an event loop, answer from the stale value and refresh in the
        # background instead of blocking the loop on the proxy.
        if _schedule_refresh(base_url):
            return _cached[1]
    enabled = _fetch_crawling_enabled(base_url)
    _cached = (monotonic(), enabled)
    return enabled


def _schedule_refresh(base_url: str) -> bool:
    global _refresh
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    if _refresh is None or _refresh[0] is not loop or _refresh[1].done():
        _refresh = (loop, loop.create_task(_refresh_cache(base_url)))
    return True


async def _refresh_cache(base_url: str) -> None:
    global _cached
    _cached = (monotonic(), await _fetch_crawling_enabled_async(base_url))


def _client(base_url: str) -> Client:
    from unique_web_search.services.proxy.bridge import SERVICE_ID

    return Client(
        base_url=base_url,
        timeout=httpx.Timeout(_TIMEOUT_SECONDS),
        headers={SERVICE_ID_HEADER: SERVICE_ID},
    )


# The proxy enforces CRAWL_ENABLED itself, so an unreachable proxy only
# affects which crawl options the tool offers.
def _fetch_crawling_enabled(base_url: str) -> bool:
    try:
        with _client(base_url) as client:
            response = list_providers.sync(client=client)
    except Exception as error:
        _LOGGER.warning(
            "Could not read crawlingEnabled from the search proxy: %s", error
        )
        return True
    return _read_crawling_enabled(response)


async def _fetch_crawling_enabled_async(base_url: str) -> bool:
    try:
        async with _client(base_url) as client:
            response = await list_providers.asyncio(client=client)
    except Exception as error:
        _LOGGER.warning(
            "Could not read crawlingEnabled from the search proxy: %s", error
        )
        return True
    return _read_crawling_enabled(response)


def _read_crawling_enabled(response: object) -> bool:
    if not isinstance(response, ProvidersListResponse):
        _LOGGER.warning("Unexpected search proxy configuration response: %r", response)
        return True
    if response.crawling_enabled is UNSET:
        return True
    return bool(response.crawling_enabled)
