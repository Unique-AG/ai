from __future__ import annotations

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


def crawling_enabled() -> bool:
    """Whether the search proxy accepts crawl requests (its ``CRAWL_ENABLED``)."""
    global _cached
    from unique_web_search.settings import env_settings

    base_url = env_settings.search_proxy_base_url
    if base_url is None:
        return True
    now = monotonic()
    if _cached is not None and now - _cached[0] < _CACHE_SECONDS:
        return _cached[1]
    enabled = _fetch_crawling_enabled(base_url)
    _cached = (now, enabled)
    return enabled


def _fetch_crawling_enabled(base_url: str) -> bool:
    # The proxy enforces CRAWL_ENABLED itself, so an unreachable proxy only
    # affects which crawl options the tool offers.
    from unique_web_search.services.proxy.bridge import SERVICE_ID

    try:
        with Client(
            base_url=base_url,
            timeout=httpx.Timeout(_TIMEOUT_SECONDS),
            headers={SERVICE_ID_HEADER: SERVICE_ID},
        ) as client:
            response = list_providers.sync(client=client)
    except Exception as error:
        _LOGGER.warning(
            "Could not read crawlingEnabled from the search proxy: %s", error
        )
        return True
    if not isinstance(response, ProvidersListResponse):
        _LOGGER.warning("Unexpected search proxy configuration response: %r", response)
        return True
    if response.crawling_enabled is UNSET:
        return True
    return bool(response.crawling_enabled)
