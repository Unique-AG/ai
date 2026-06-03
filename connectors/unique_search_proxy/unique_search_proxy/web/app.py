from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from unique_search_proxy.web.api import health_router, v1_router
from unique_search_proxy.web.core.client.service import create_http_client_pool
from unique_search_proxy.web.core.errors import register_exception_handlers
from unique_search_proxy.web.core.providers import register_builtin_providers
from unique_search_proxy.web.monitoring import setup_prometheus

load_dotenv()

_LOGGER = logging.getLogger(__name__)


class HealthCheckFilter(logging.Filter):
    """Filter out health check requests from access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if "GET" in message and any(
            path in message for path in ("/health", "/ready", "/metrics")
        ):
            return False
        return True


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    _LOGGER.info("Starting Unique Search Proxy...")
    pool = await create_http_client_pool()
    app.state.http_client_pool = pool
    try:
        yield
    finally:
        await pool.aclose()
        _LOGGER.info("Shutting down Unique Search Proxy...")


def create_app() -> FastAPI:
    register_builtin_providers()
    application = FastAPI(
        title="Unique Search Proxy",
        description="Unified web egress proxy for search engines and crawlers",
        version="0.2.0",
        lifespan=lifespan,
    )
    register_exception_handlers(application)
    setup_prometheus(application)
    application.include_router(health_router)
    application.include_router(v1_router)
    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=2349)
