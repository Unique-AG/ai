from __future__ import annotations

import time

from prometheus_client import Counter, Gauge, Histogram

from .registry import REGISTRY

_http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)
_http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
    registry=REGISTRY,
)
_http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "In-flight HTTP requests",
    ["method"],
    registry=REGISTRY,
)

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
    """

    def __init__(self, app, excluded_paths: set[str] | None = None):
        self.app = app
        self._excluded_paths = (
            excluded_paths if excluded_paths is not None else _DEFAULT_EXCLUDED_PATHS
        )

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
            _http_request_duration_seconds.labels(method=method, path=path).observe(
                duration
            )
            _http_requests_total.labels(
                method=method, path=path, status_code=status_code
            ).inc()
