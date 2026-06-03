from fastapi import APIRouter

from unique_search_proxy.web.api.v1.crawl import router as crawl_router
from unique_search_proxy.web.api.v1.search import router as search_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(search_router)
v1_router.include_router(crawl_router)

__all__ = ["v1_router"]
