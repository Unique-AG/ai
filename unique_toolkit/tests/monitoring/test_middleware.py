"""Tests for unique_toolkit.monitoring.middleware module."""

import pytest

import unique_toolkit.monitoring.middleware as middleware_module
from unique_toolkit.monitoring.middleware import MetricsMiddleware

# ---------------------------------------------------------------------------
# Minimal ASGI app helpers
# ---------------------------------------------------------------------------


def _make_http_scope(path: str = "/api/data", method: str = "GET") -> dict:
    return {"type": "http", "path": path, "method": method}


def _make_non_http_scope(scope_type: str = "lifespan") -> dict:
    return {"type": scope_type}


async def _simple_app(scope, receive, send):
    """Minimal ASGI app that returns 200."""
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b""})


async def _app_with_status(status: int):
    """Return an ASGI app that responds with a specific status code."""

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    return app


async def _crashing_app(scope, receive, send):
    """ASGI app that raises an exception before sending a response."""
    raise RuntimeError("app crashed")


# ---------------------------------------------------------------------------
# Pass-through behaviour
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_middleware__passes_through__non_http_scope() -> None:
    """
    Purpose: Verify MetricsMiddleware passes non-HTTP scopes (WebSocket, lifespan) through unchanged.
    Why this matters: Instrumenting non-HTTP scopes would cause metrics corruption.
    Setup summary: Call middleware with a lifespan scope, assert inner app was called.
    """
    called = []

    async def inner(scope, receive, send):
        called.append(scope["type"])

    middleware = MetricsMiddleware(inner)
    scope = _make_non_http_scope("lifespan")

    await middleware(scope, None, None)

    assert called == ["lifespan"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_middleware__passes_through__default_excluded_paths() -> None:
    """
    Purpose: Verify MetricsMiddleware skips tracking for default excluded paths (/health, /metrics, /).
    Why this matters: Tracking health check endpoints inflates request counts and pollutes latency data.
    Setup summary: Call middleware with /health path, assert inner app called without recording metrics.
    """
    called = []

    async def inner(scope, receive, send):
        called.append(scope.get("path"))

    middleware = MetricsMiddleware(inner)

    for path in ["/health", "/metrics", "/"]:
        called.clear()
        await middleware(_make_http_scope(path=path), None, None)
        assert called == [path], f"Expected pass-through for {path}"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_middleware__passes_through__custom_excluded_paths() -> None:
    """
    Purpose: Verify MetricsMiddleware respects custom excluded_paths argument.
    Why this matters: Operators may need to exclude additional paths like /readyz or /livez.
    Setup summary: Pass excluded_paths={"/readyz"}, call with /readyz, assert inner app called.
    """
    called = []

    async def inner(scope, receive, send):
        called.append(scope.get("path"))

    middleware = MetricsMiddleware(inner, excluded_paths={"/readyz"})
    await middleware(_make_http_scope(path="/readyz"), None, None)

    assert called == ["/readyz"]


# ---------------------------------------------------------------------------
# Normal request tracking
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_middleware__captures_status_code__from_response_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify the send_wrapper captures status_code from http.response.start message.
    Why this matters: The recorded status_code label on http_requests_total must match the actual HTTP response.
    Setup summary: Intercept http.response.start inside _simple_app, verify status is "200".
    """
    captured_statuses: list[str] = []

    def mock_labels(**kwargs):
        captured_statuses.append(kwargs.get("status_code", ""))

        class _FakeCounter:
            def inc(self):
                pass

        return _FakeCounter()

    monkeypatch.setattr(middleware_module._http_requests_total, "labels", mock_labels)

    middleware = MetricsMiddleware(_simple_app)
    scope = _make_http_scope(path="/api/data", method="GET")
    sent: list[dict] = []

    async def receive():
        return {}

    async def send(msg):
        sent.append(msg)

    await middleware(scope, receive, send)

    assert "200" in captured_statuses


@pytest.mark.ai
@pytest.mark.asyncio
async def test_middleware__tracks_request__for_non_excluded_path() -> None:
    """
    Purpose: Verify MetricsMiddleware calls the inner app for non-excluded paths.
    Why this matters: If the middleware accidentally excludes legitimate paths, requests are dropped.
    Setup summary: Call middleware with /api/endpoint, assert inner app ran and sent a response.
    """
    sent: list[dict] = []

    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = MetricsMiddleware(inner)

    async def collect_send(msg):
        sent.append(msg)

    await middleware(_make_http_scope(path="/api/endpoint"), None, collect_send)

    response_start = next(m for m in sent if m["type"] == "http.response.start")
    assert response_start["status"] == 201


@pytest.mark.ai
@pytest.mark.asyncio
async def test_middleware__propagates_exception__from_crashing_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify MetricsMiddleware re-raises exceptions from the inner app.
    Why this matters: Swallowing exceptions would mask errors and break error propagation to ASGI server.
    Setup summary: Use _crashing_app as inner app, assert RuntimeError propagates through middleware.
    """
    # Suppress actual Prometheus inc/observe to avoid side effects in error path
    monkeypatch.setattr(
        middleware_module._http_requests_in_progress.labels(method="GET"),
        "inc",
        lambda: None,
    )

    middleware = MetricsMiddleware(_crashing_app)

    with pytest.raises(RuntimeError, match="app crashed"):
        await middleware(_make_http_scope(), None, None)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_middleware__default_status_500__when_app_crashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify default status_code is "500" when app crashes before sending response.
    Why this matters: Recording crashed requests as 500 keeps error rate dashboards accurate.
    Setup summary: Intercept _http_requests_total.labels call, use crashing app, assert "500" recorded.
    """
    captured: list[str] = []

    def mock_labels(**kwargs):
        captured.append(kwargs.get("status_code", ""))

        class _FakeCounter:
            def inc(self):
                pass

        return _FakeCounter()

    monkeypatch.setattr(middleware_module._http_requests_total, "labels", mock_labels)

    middleware = MetricsMiddleware(_crashing_app)

    with pytest.raises(RuntimeError):
        await middleware(_make_http_scope(), None, None)

    assert "500" in captured


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_middleware__uses_default_excluded_paths__when_none_given() -> None:
    """
    Purpose: Verify MetricsMiddleware defaults to {"/health", "/metrics", "/"} when excluded_paths=None.
    Why this matters: Changing the default by accident would cause health endpoints to be tracked.
    Setup summary: Instantiate with excluded_paths=None, assert _excluded_paths matches defaults.
    """
    middleware = MetricsMiddleware(_simple_app, excluded_paths=None)

    assert middleware._excluded_paths == frozenset({"/health", "/metrics", "/"})


@pytest.mark.ai
def test_middleware__uses_custom_excluded_paths__when_provided() -> None:
    """
    Purpose: Verify MetricsMiddleware stores provided excluded_paths.
    Why this matters: Custom exclusions must override defaults completely.
    Setup summary: Pass {"/custom"}, assert _excluded_paths is {"/custom"}.
    """
    middleware = MetricsMiddleware(_simple_app, excluded_paths={"/custom"})

    assert middleware._excluded_paths == {"/custom"}
