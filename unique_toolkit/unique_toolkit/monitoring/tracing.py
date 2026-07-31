"""OpenTelemetry tracing bootstrap for toolkit consumers."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, Iterable, MutableMapping
from typing import TYPE_CHECKING, TypeAlias, cast

if TYPE_CHECKING:
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

ASGIScope: TypeAlias = MutableMapping[str, object]
ASGIMessage: TypeAlias = MutableMapping[str, object]
ASGIReceive: TypeAlias = Callable[[], Awaitable[ASGIMessage]]
ASGISend: TypeAlias = Callable[[ASGIMessage], Awaitable[None]]
ASGIApp: TypeAlias = Callable[[ASGIScope, ASGIReceive, ASGISend], Awaitable[None]]

_OTEL_EXTRA_MESSAGE = (
    "OpenTelemetry tracing requires the unique_toolkit[otel] extra. "
    "Install it with: uv add 'unique-toolkit[otel]'"
)


def _resolve_exporter() -> str | None:
    """Resolve standard OTel settings with Node service compatibility aliases."""
    exporter_name = os.getenv("OTEL_TRACES_EXPORTER")
    if exporter_name:
        return exporter_name

    enabled = os.getenv("ENABLE_OPENTELEMETRY")
    if enabled == "false":
        return None
    if enabled == "true":
        return os.getenv("OTEL_SPAN_PROCESSOR") or "otlp"

    if os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    ):
        return "otlp"
    return None


def _missing_otel_extra() -> ImportError:
    """Create a consistent error for an unavailable optional tracing dependency."""
    return ImportError(_OTEL_EXTRA_MESSAGE)


def _trace_context_propagator() -> TraceContextTextMapPropagator:
    """Return a W3C trace-context propagator without forwarding baggage."""
    try:
        from opentelemetry.trace.propagation.tracecontext import (
            TraceContextTextMapPropagator,
        )
    except ImportError as error:
        raise _missing_otel_extra() from error
    return TraceContextTextMapPropagator()


class TraceContextMiddleware:
    """ASGI middleware that continues W3C trace context with one server span."""

    def __init__(self, app: ASGIApp, span_name: str = "HTTP request") -> None:
        self.app: ASGIApp = app
        self._span_name: str = span_name

    async def __call__(
        self, scope: ASGIScope, receive: ASGIReceive, send: ASGISend
    ) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        try:
            from opentelemetry import trace
            from opentelemetry.trace import SpanKind
        except ImportError as error:
            raise _missing_otel_extra() from error

        headers: dict[str, str] = {}
        raw_headers = cast(Iterable[tuple[bytes, bytes]], scope.get("headers", ()))
        for name, value in raw_headers:
            key = name.decode("latin-1").lower()
            if key not in {"traceparent", "tracestate"}:
                continue
            header_value = value.decode("latin-1")
            if key == "tracestate" and key in headers:
                headers[key] = f"{headers[key]},{header_value}"
            elif key not in headers:
                headers[key] = header_value
        parent_context = _trace_context_propagator().extract(headers)
        with trace.get_tracer(__name__).start_as_current_span(
            self._span_name,
            context=parent_context,
            kind=SpanKind.SERVER,
        ):
            return await self.app(scope, receive, send)


def inject_trace_headers(headers: MutableMapping[str, str]) -> None:
    """Inject the active W3C trace context into outgoing request headers."""
    _trace_context_propagator().inject(headers)


def configure_tracing(
    *,
    service_name: str | None = None,
    service_version: str | None = None,
) -> bool:
    """Install an OpenTelemetry trace provider from standard and Node-compatible env.

    ``OTEL_TRACES_EXPORTER`` takes precedence. When it is unset,
    ``ENABLE_OPENTELEMETRY`` and ``OTEL_SPAN_PROCESSOR`` mirror the Node service
    tracing configuration. Prometheus metrics and application logging remain
    separate, so ``OTEL_METRICS_READER`` and ``OTEL_LOGS_PROCESSOR`` are ignored.
    """
    exporter_name = _resolve_exporter()

    if exporter_name in {None, "none"}:
        return False

    if exporter_name not in {None, "console", "otlp"}:
        raise ValueError(
            "Unsupported trace exporter. Expected 'none', 'console', or 'otlp'."
        )

    try:
        from opentelemetry import trace
        from opentelemetry.trace import ProxyTracerProvider
    except ImportError as error:
        raise _missing_otel_extra() from error

    if not isinstance(trace.get_tracer_provider(), ProxyTracerProvider):
        return True

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
            SimpleSpanProcessor,
        )
    except ImportError as error:
        raise _missing_otel_extra() from error

    attributes: dict[str, str] = {}
    resolved_service_name = (
        service_name if service_name is not None else os.getenv("OTEL_SERVICE_NAME")
    )
    resolved_service_version = (
        service_version
        if service_version is not None
        else os.getenv("OTEL_SERVICE_VERSION", os.getenv("VERSION"))
    )
    if resolved_service_name is not None:
        attributes["service.name"] = resolved_service_name
    if resolved_service_version is not None:
        attributes["service.version"] = resolved_service_version

    provider = TracerProvider(resource=Resource.create(attributes))
    if exporter_name == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return True
