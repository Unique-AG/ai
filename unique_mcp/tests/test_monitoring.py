"""Tests for unique_mcp.monitoring helpers."""

from __future__ import annotations

import pytest
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.testclient import TestClient

from unique_mcp.monitoring import setup_ops


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
