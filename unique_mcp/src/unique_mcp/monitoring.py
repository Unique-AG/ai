"""Ops routes (/probe, /health, /metrics) + HTTP and MCP Prometheus metrics."""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence

from fastmcp import FastMCP
from fastmcp.server.middleware import CallNext, MiddlewareContext
from fastmcp.server.middleware import Middleware as McpMw
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from unique_toolkit.monitoring import MetricNamespace, MetricsMiddleware, get_metrics

_EXCLUDED = frozenset({"/", "/probe", "/health", "/ready", "/metrics", "/favicon.ico"})
_OPS = FastMCP(name="unique-mcp-ops")
_log = logging.getLogger("unique_mcp")
_m = MetricNamespace("mcp")
_calls = _m.counter("calls_total", "MCP calls", ["kind", "name", "status"])
_duration = _m.histogram("call_duration_seconds", "MCP call duration", ["kind", "name"])


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


class _McpMetrics(McpMw):
    async def _track(self, kind: str, name: str, context: MiddlewareContext, call_next):
        start = time.perf_counter()
        status = "ok"
        err: BaseException | None = None
        try:
            return await call_next(context)
        except Exception as e:
            status = type(e).__name__
            err = e
            raise
        finally:
            elapsed = time.perf_counter() - start
            _duration.labels(kind=kind, name=name).observe(elapsed)
            _calls.labels(kind=kind, name=name, status=status).inc()
            # LogRecord reserves `name`; use `operation` for the MCP name.
            extra = {
                "kind": kind,
                "operation": name,
                "status": status,
                "duration_ms": round(elapsed * 1000, 2),
            }
            if err is not None:
                _log.error("%s '%s' failed", kind, name, exc_info=err, extra=extra)
            else:
                _log.info("%s '%s' completed", kind, name, extra=extra)

    async def on_call_tool(self, context: MiddlewareContext, call_next: CallNext):
        return await self._track(
            "tool", getattr(context.message, "name", "unknown"), context, call_next
        )

    async def on_read_resource(self, context: MiddlewareContext, call_next: CallNext):
        return await self._track(
            "resource",
            str(getattr(context.message, "uri", "unknown")),
            context,
            call_next,
        )

    async def on_get_prompt(self, context: MiddlewareContext, call_next: CallNext):
        return await self._track(
            "prompt", getattr(context.message, "name", "unknown"), context, call_next
        )


def setup_ops(
    mcp: FastMCP,
    *,
    excluded_paths: set[str] | None = None,
    duration_buckets: Sequence[float] | None = None,
) -> Middleware:
    """Mount ops routes + MCP metrics; return HTTP metrics middleware.

    FastMCP owns MCP ``tools/call`` spans (continues ``_meta.traceparent`` /
    an active context). Call ``configure_tracing()`` at startup so those spans
    export. HTTP ``TraceContextMiddleware`` is intentionally not installed —
    on streamable HTTP it often creates an orphan root beside FastMCP's tree.

    Idempotent for MCP mount/middleware: a second call on the same ``mcp`` does
    not remount ops or attach another ``_McpMetrics`` (which would inflate
    ``mcp_*``). Append the returned Starlette ``Middleware`` only once.
    """
    if not any(getattr(p, "server", None) is _OPS for p in mcp.providers):
        mcp.mount(_OPS)
    if not any(isinstance(mw, _McpMetrics) for mw in mcp.middleware):
        mcp.add_middleware(_McpMetrics())
    return Middleware(
        MetricsMiddleware,
        excluded_paths=excluded_paths if excluded_paths is not None else set(_EXCLUDED),
        duration_buckets=duration_buckets,
    )
