"""OpenTelemetry tracing bootstrap for toolkit consumers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, MutableMapping
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar, Self, TypeAlias, cast

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

# Keep ASGI aliases local; tracing should not depend on asgiref solely for typing.
ASGIScope: TypeAlias = MutableMapping[str, object]
ASGIMessage: TypeAlias = MutableMapping[str, object]
ASGIReceive: TypeAlias = Callable[[], Awaitable[ASGIMessage]]
ASGISend: TypeAlias = Callable[[ASGIMessage], Awaitable[None]]
ASGIApp: TypeAlias = Callable[[ASGIScope, ASGIReceive, ASGISend], Awaitable[None]]

_OTEL_EXTRA_MESSAGE = (
    "OpenTelemetry tracing requires the unique_toolkit[otel] extra. "
    "Install it with: uv add 'unique-toolkit[otel]'"
)


class TraceExporter(StrEnum):
    """Trace exporters supported by the toolkit bootstrap."""

    NONE = "none"
    CONSOLE = "console"
    OTLP = "otlp"


class TracingSettings(BaseSettings):
    """Environment settings for optional OpenTelemetry tracing."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="OTEL_",
        env_ignore_empty=True,
        extra="ignore",
    )

    traces_exporter: TraceExporter | None = None
    service_name: str | None = None
    service_version: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OTEL_SERVICE_VERSION", "VERSION"),
    )
    otlp_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            "OTEL_EXPORTER_OTLP_ENDPOINT",
        ),
    )
    span_processor: TraceExporter | None = None
    enabled: bool | None = Field(
        default=None,
        validation_alias="ENABLE_OPENTELEMETRY",
    )

    @property
    def exporter(self) -> TraceExporter | None:
        """Resolve standard OTel settings with Node service compatibility aliases."""
        if self.traces_exporter:
            return self.traces_exporter
        if self.otlp_endpoint:
            return TraceExporter.OTLP
        if self.enabled is False:
            return None
        if self.enabled is True:
            return self.span_processor or TraceExporter.OTLP
        return None

    @classmethod
    def try_load(cls) -> Self | None:
        """Load env settings, or ``None`` when tracing cannot be enabled."""
        settings = cls()
        if settings.exporter in {None, TraceExporter.NONE}:
            return None
        return settings


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
    settings = TracingSettings.try_load()
    if settings is None:
        return False
    exporter = settings.exporter
    assert exporter is not None  # try_load guarantees a concrete exporter

    try:
        from opentelemetry import trace
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
        from opentelemetry.trace import ProxyTracerProvider
    except ImportError as error:
        raise _missing_otel_extra() from error

    if not isinstance(trace.get_tracer_provider(), ProxyTracerProvider):
        return True

    name = service_name if service_name is not None else settings.service_name
    version = (
        service_version if service_version is not None else settings.service_version
    )
    attributes = {
        key: value
        for key, value in (("service.name", name), ("service.version", version))
        if value is not None
    }

    provider = TracerProvider(resource=Resource.create(attributes))
    if exporter is TraceExporter.CONSOLE:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return True
