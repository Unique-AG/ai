"""Tests for unique_mcp.monitoring helpers."""

from __future__ import annotations

import pytest
from fastmcp import Client, FastMCP
from starlette.middleware import Middleware
from starlette.testclient import TestClient
from unique_toolkit.monitoring import MetricsMiddleware, get_metrics

from unique_mcp.monitoring import _OPS, _McpMetrics, setup_ops


@pytest.mark.ai
@pytest.mark.unit
def test_setup_ops__mounts_probe_health_and_metrics() -> None:
    """
    Purpose: Verify setup_ops mounts /probe, /health, and /metrics.
    Why this matters: Platform probes and ServiceMonitors need these paths.
    Setup summary: Call setup_ops on a FastMCP app and GET each route.
    """
    mcp = FastMCP("test-server")
    middleware = setup_ops(mcp)
    client = TestClient(mcp.http_app())

    probe = client.get("/probe")
    health = client.get("/health")
    metrics = client.get("/metrics")

    assert probe.status_code == 200
    assert probe.json()["status"] == "ok"
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"
    assert metrics.status_code == 200
    assert "text/plain" in metrics.headers["content-type"]
    assert metrics.text
    assert isinstance(middleware, Middleware)
    assert middleware.cls is MetricsMiddleware


@pytest.mark.ai
@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_ops__auto_instruments_mcp_calls() -> None:
    """
    Purpose: Verify setup_ops metrics cover tools/resources and error types.
    Why this matters: HTTP path metrics alone cannot distinguish MCP operations.
    Setup summary: Register tool + resource, call setup_ops, invoke via Client.
    """
    mcp = FastMCP("metrics-server")

    @mcp.tool
    def ping() -> str:
        return "pong"

    @mcp.tool
    def boom() -> str:
        raise RuntimeError("nope")

    @mcp.resource("resource://note")
    def note() -> str:
        return "hi"

    setup_ops(mcp)

    async with Client(mcp) as client:
        assert (await client.call_tool("ping")).is_error is False
        with pytest.raises(Exception):
            await client.call_tool("boom")
        assert await client.read_resource("resource://note")

    body = get_metrics().decode()
    assert 'mcp_calls_total{kind="tool",name="ping",status="ok"}' in body
    assert 'mcp_calls_total{kind="tool",name="boom",status="ToolError"}' in body
    assert 'mcp_calls_total{kind="resource",name="resource://note",status="ok"}' in body
    assert 'mcp_call_duration_seconds_count{kind="tool",name="ping"}' in body
    assert (
        'mcp_call_duration_seconds_count{kind="resource",name="resource://note"}'
        in body
    )


@pytest.mark.ai
@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_ops__idempotent_mcp_metrics() -> None:
    """
    Purpose: Verify calling setup_ops twice does not double-count MCP metrics.
    Why this matters: Entrypoints that set up ops in more than one place must
    not inflate mcp_calls_total.
    Setup summary: setup_ops twice, call one tool, assert counter is 1.
    """
    mcp = FastMCP("idempotent-server")

    @mcp.tool
    def idempotent_ping() -> str:
        return "pong"

    setup_ops(mcp)
    setup_ops(mcp)

    assert sum(isinstance(mw, _McpMetrics) for mw in mcp.middleware) == 1
    assert sum(getattr(p, "server", None) is _OPS for p in mcp.providers) == 1

    async with Client(mcp) as client:
        assert (await client.call_tool("idempotent_ping")).is_error is False

    body = get_metrics().decode()
    assert 'mcp_calls_total{kind="tool",name="idempotent_ping",status="ok"} 1.0' in body
