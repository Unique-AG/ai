from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

import unique_search_proxy_client.web.settings.monitoring as monitoring_settings
from unique_search_proxy_client.web.monitoring.metrics import HTTP_LATENCY_BUCKETS

_LOGGER = logging.getLogger(__name__)

_METRICS_EXCLUDED_PATHS = frozenset(
    {
        "/",
        "/health",
        "/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)


def setup_prometheus(app: FastAPI) -> bool:
    """Attach HTTP metrics middleware and expose GET /metrics when enabled."""
    if not monitoring_settings.prometheus_settings.enabled:
        _LOGGER.info("Prometheus metrics disabled via settings")
        return False

    try:
        from unique_toolkit.monitoring import MetricsMiddleware, get_metrics
    except ImportError:
        _LOGGER.warning(
            "unique_toolkit.monitoring not available; install unique-toolkit[monitoring]"
        )
        return False

    app.add_middleware(
        MetricsMiddleware,
        excluded_paths=set(_METRICS_EXCLUDED_PATHS),
        duration_buckets=HTTP_LATENCY_BUCKETS,
    )

    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> PlainTextResponse:
        return PlainTextResponse(
            get_metrics(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    _LOGGER.info("Prometheus metrics enabled at /metrics")
    return True
