"""Runtime provider discovery for search and crawl execution."""

from __future__ import annotations

from fastapi import APIRouter
from unique_search_proxy_core.schema import ProvidersListResponse

from unique_search_proxy_client.web.core.registry import list_registered_providers

router = APIRouter(prefix="/configuration", tags=["configuration"])


@router.get(
    "/providers",
    response_model=ProvidersListResponse,
    summary="List registered search engines and crawlers",
)
async def list_providers() -> ProvidersListResponse:
    providers = list_registered_providers()
    return ProvidersListResponse(
        search_engines=providers["search_engines"],
        agent_engines=providers["agent_engines"],
        crawlers=providers["crawlers"],
    )


__all__ = ["router"]
