from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from unique_search_proxy_core.context import (
    LOCAL_REQUEST_CONTEXT,
    SERVICE_ID_HEADER,
    RequestContext,
)
from unique_search_proxy_sdk import UniqueSearchProxyClient

from unique_web_search import activity_record
from unique_web_search.settings import env_settings

SERVICE_ID = "assistants-core"

search_proxy_client_enabled = env_settings.search_proxy_base_url is not None


async def _note_response(_: httpx.Response) -> None:
    activity_record.note_response_received()


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
        http_client = client.openapi.get_async_httpx_client()
        http_client.headers[SERVICE_ID_HEADER] = SERVICE_ID
        # Runs before the SDK raises on 4xx/5xx, so an error status still counts as a response.
        http_client.event_hooks["response"].append(_note_response)
        yield client


__all__ = [
    "open_search_proxy_client",
    "search_proxy_client_enabled",
]
