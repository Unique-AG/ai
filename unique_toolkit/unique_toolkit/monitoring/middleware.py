from __future__ import annotations

import time
from collections.abc import Sequence

from prometheus_client import (  # pyright: ignore[reportMissingImports]
    Counter,
    Gauge,
    Histogram,
)

from .registry import REGISTRY

_http_requests_total = Counter(
    "python_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)
_http_requests_in_progress = Gauge(
    "python_http_requests_in_progress",
    "In-flight HTTP requests",
    ["method"],
    registry=REGISTRY,
    multiprocess_mode="livesum",
)

# Created lazily on first MetricsMiddleware construction so services can choose the
# bucket layout. Prometheus allows a metric name to be registered only once per
# registry, so the buckets passed to the first middleware win for the process.
_http_request_duration_seconds: Histogram | None = None


def _get_or_create_duration_histogram(
    buckets: Sequence[float] | None,
) -> Histogram:
    global _http_request_duration_seconds
    if _http_request_duration_seconds is None:
        if buckets is None:
            _http_request_duration_seconds = Histogram(
                "python_http_request_duration_seconds",
                "HTTP request duration",
                ["method", "path"],
                registry=REGISTRY,
            )
        else:
            _http_request_duration_seconds = Histogram(
                "python_http_request_duration_seconds",
                "HTTP request duration",
                ["method", "path"],
                registry=REGISTRY,
                buckets=tuple(buckets),
            )
    return _http_request_duration_seconds


_DEFAULT_EXCLUDED_PATHS = frozenset({"/health", "/metrics", "/"})


class MetricsMiddleware:
    """ASGI middleware that tracks HTTP request metrics.

    Works with any ASGI app (FastAPI, Quart, Starlette).

    Handles:
    - Non-HTTP scopes (WebSocket, lifespan) — passed through, not tracked
    - Excluded paths (health, metrics) — passed through, not tracked
    - App exceptions — duration + error still recorded, in-progress gauge cleaned up
    - Streaming responses — status captured from first http.response.start message

    Usage::

        # FastAPI
        app.add_middleware(MetricsMiddleware)

        # Quart
        app.asgi_app = MetricsMiddleware(app.asgi_app)

    ``duration_buckets`` overrides the latency histogram buckets (seconds). Without
    it, prometheus_client's defaults apply and their top finite bucket is 10s —
    histogram_quantile cannot resolve past the largest finite bucket, so services
    with slower endpoints should pass buckets covering their full latency range::

        app.add_middleware(MetricsMiddleware, duration_buckets=(1, 5, 30, 60, 120))

    The histogram is registered once per process; the buckets of the first
    constructed middleware apply.
    """

    def __init__(
        self,
        app,
        excluded_paths: set[str] | None = None,
        duration_buckets: Sequence[float] | None = None,
    ):
        self.app = app
        self._excluded_paths = (
            excluded_paths if excluded_paths is not None else _DEFAULT_EXCLUDED_PATHS
        )
        self._duration = _get_or_create_duration_histogram(duration_buckets)

    async def __call__(self, scope, receive, send):
        # Pass through non-HTTP (WebSocket, lifespan)
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "/")

        # Pass through excluded paths (health checks, metrics endpoint)
        if path in self._excluded_paths:
            return await self.app(scope, receive, send)

        method = scope.get("method", "UNKNOWN")
        status_code = "500"  # Default if app crashes before sending response

        _http_requests_in_progress.labels(method=method).inc()
        start = time.perf_counter()

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = str(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            _http_requests_in_progress.labels(method=method).dec()
            self._duration.labels(method=method, path=path).observe(duration)
            _http_requests_total.labels(
                method=method, path=path, status_code=status_code
            ).inc()
