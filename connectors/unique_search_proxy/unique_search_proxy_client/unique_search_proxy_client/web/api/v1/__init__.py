from fastapi import APIRouter, Depends

from unique_search_proxy_client.web.api.v1.agent_search import (
    router as agent_search_router,
)
from unique_search_proxy_client.web.api.v1.configuration import (
    router as configuration_router,
)
from unique_search_proxy_client.web.api.v1.context_headers import (
    document_request_context_headers,
)
from unique_search_proxy_client.web.api.v1.crawl import router as crawl_router
from unique_search_proxy_client.web.api.v1.search import router as search_router

v1_router = APIRouter(
    prefix="/v1",
    dependencies=[Depends(document_request_context_headers)],
)
v1_router.include_router(configuration_router)
v1_router.include_router(search_router)
v1_router.include_router(agent_search_router)
v1_router.include_router(crawl_router)

__all__ = ["v1_router"]
