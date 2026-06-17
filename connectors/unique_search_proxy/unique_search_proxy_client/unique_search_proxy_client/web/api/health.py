from __future__ import annotations

from fastapi import APIRouter, Request

from unique_search_proxy_client.web.core.client import get_http_client_pool
from unique_search_proxy_client.web.core.registry import (
    registered_agent_engines,
    registered_crawlers,
    registered_search_engines,
)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/ready")
async def ready(request: Request) -> dict[str, object]:
    pool = get_http_client_pool(request.app)
    return {
        "status": "ready",
        "httpClient": "ok" if not pool.client.is_closed else "closed",
        "searchEngines": sorted(registered_search_engines()),
        "agentEngines": sorted(registered_agent_engines()),
        "crawlers": sorted(registered_crawlers()),
    }
