from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from unique_search_proxy_core.logging import suppress_httpx_request_logs

# Application entrypoint only. HTTP SDK lives in unique_search_proxy_sdk.
from unique_search_proxy_client.web.api import health_router, v1_router
from unique_search_proxy_client.web.core.agent_engines.bing.cleanup import (
    maybe_cleanup_auto_provisioned_bing_agents_on_start,
)
from unique_search_proxy_client.web.core.agent_engines.bing.client import (
    aclose_private_endpoint_http_client,
)
from unique_search_proxy_client.web.core.client.service import create_http_client_pool
from unique_search_proxy_client.web.core.providers import register_builtin_providers
from unique_search_proxy_client.web.error_handlers import register_exception_handlers
from unique_search_proxy_client.web.logging_config import (
    build_logging_config,
    configure_logging,
)
from unique_search_proxy_client.web.middleware.context import RequestContextMiddleware
from unique_search_proxy_client.web.monitoring import setup_prometheus
from unique_search_proxy_client.web.startup_report import (
    log_startup_settings_report,
)

if "pytest" not in sys.modules:
    load_dotenv()

configure_logging()
suppress_httpx_request_logs()

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
    log_startup_settings_report(_LOGGER)
    await maybe_cleanup_auto_provisioned_bing_agents_on_start()
    pool = await create_http_client_pool()
    app.state.http_client_pool = pool
    try:
        yield
    finally:
        await aclose_private_endpoint_http_client()
        await pool.aclose()
        _LOGGER.info("Shutting down Unique Search Proxy...")


def create_app() -> FastAPI:
    register_builtin_providers()
    application = FastAPI(
        title="Unique Search Proxy",
        description=(
            "Unified web egress proxy for search engines and crawlers. "
            "Use **Try it out** on `/v1/search` and `/v1/crawl` — pick an example "
            "from the request-body dropdown (snippets-only Google search, crawl with "
            "HTML markdown, etc.). `/v1/*` routes accept tenant context headers "
            "(`x-unique-company-id`, `x-unique-user-id`, `x-unique-chat-id`; "
            "defaults `local` in Swagger). Requires provider env vars (e.g. "
            "`GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID`) for live calls."
        ),
        version="0.2.0",
        lifespan=lifespan,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 1,
            "defaultModelExpandDepth": 2,
            "docExpansion": "list",
            "tryItOutEnabled": True,
            "displayRequestDuration": True,
        },
    )
    register_exception_handlers(application)
    setup_prometheus(application)
    application.add_middleware(RequestContextMiddleware)
    application.include_router(health_router)
    application.include_router(v1_router)
    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=2349,
        log_config=build_logging_config(),
    )
