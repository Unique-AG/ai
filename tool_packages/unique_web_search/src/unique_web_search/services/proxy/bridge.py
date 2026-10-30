from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from unique_search_proxy_core.context import (
    LOCAL_REQUEST_CONTEXT,
    SERVICE_ID_HEADER,
    RequestContext,
)
from unique_search_proxy_sdk import UniqueSearchProxyClient

from unique_web_search.settings import env_settings

SERVICE_ID = "assistants-core"

search_proxy_client_enabled = env_settings.search_proxy_base_url is not None


@asynccontextmanager
async def open_search_proxy_client(
    timeout: float,
    context: RequestContext = LOCAL_REQUEST_CONTEXT,
) -> AsyncIterator[UniqueSearchProxyClient]:
    base_url = env_settings.search_proxy_base_url
    assert base_url is not None, "Unique Search Proxy base URL is not configured"

    async with UniqueSearchProxyClient(
        base_url=base_url,
        timeout=timeout,
        context=context,
    ) as client:
        client.openapi.get_async_httpx_client().headers[SERVICE_ID_HEADER] = SERVICE_ID
        yield client


__all__ = [
    "open_search_proxy_client",
    "search_proxy_client_enabled",
]
