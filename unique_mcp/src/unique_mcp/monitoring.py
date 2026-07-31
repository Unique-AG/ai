"""Ops routes (/probe, /health, /metrics) + toolkit Prometheus middleware."""

from __future__ import annotations

from collections.abc import Sequence

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from unique_toolkit.monitoring import MetricsMiddleware, get_metrics

_EXCLUDED = frozenset({"/", "/probe", "/health", "/ready", "/metrics", "/favicon.ico"})

_OPS = FastMCP(name="unique-mcp-ops")


@_OPS.custom_route("/probe", methods=["GET"])
@_OPS.custom_route("/health", methods=["GET"])
async def _liveness(request: Request) -> JSONResponse:
    status = "healthy" if request.url.path.endswith("/health") else "ok"
    return JSONResponse({"status": status})


@_OPS.custom_route("/metrics", methods=["GET"])
async def _metrics(_request: Request) -> PlainTextResponse:
    return PlainTextResponse(
        content=get_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


def setup_ops(
    mcp: FastMCP,
    *,
    excluded_paths: set[str] | None = None,
    duration_buckets: Sequence[float] | None = None,
) -> Middleware:
    """Mount ops routes on ``mcp``; return metrics middleware."""
    mcp.mount(_OPS)
    return Middleware(
        MetricsMiddleware,
        excluded_paths=excluded_paths if excluded_paths is not None else set(_EXCLUDED),
        duration_buckets=duration_buckets,
    )
