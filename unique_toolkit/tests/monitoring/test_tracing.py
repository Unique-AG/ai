"""Tests for the optional OpenTelemetry tracing bootstrap."""

from __future__ import annotations

import builtins
from pathlib import Path

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.util._once import Once

from unique_toolkit.monitoring import (
    TraceContextMiddleware,
    TraceExporter,
    TracingSettings,
    configure_tracing,
    inject_trace_headers,
    instrument_fastapi_app,
    instrument_requests,
)


def _reset_tracer_provider() -> None:
    trace._TRACER_PROVIDER = None  # noqa: SLF001
    trace._TRACER_PROVIDER_SET_ONCE = Once()  # noqa: SLF001


@pytest.fixture(autouse=True)
def _clean_tracer_provider():
    _reset_tracer_provider()
    yield
    _reset_tracer_provider()


@pytest.mark.ai
@pytest.mark.unit
def test_configure_tracing__returns_false__when_exporter_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify explicit trace disabling does not install a provider.
    Why this matters: Prometheus-only deployments must remain free of OTel initialization.
    Setup summary: Set the exporter to none and assert configuration reports disabled.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")

    assert configure_tracing() is False


@pytest.mark.ai
@pytest.mark.unit
def test_configure_tracing__returns_false__without_exporter_or_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify unset tracing configuration is a no-op.
    Why this matters: OTel must stay opt-in for existing toolkit consumers.
    Setup summary: Clear exporter and endpoint variables and assert configuration is disabled.
    """
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.delenv("ENABLE_OPENTELEMETRY", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    assert configure_tracing() is False


@pytest.mark.ai
@pytest.mark.unit
@pytest.mark.parametrize(
    ("processor", "expected"),
    [
        ("console", TraceExporter.CONSOLE),
        ("none", TraceExporter.NONE),
    ],
)
def test_resolve_exporter__maps_node_alias__when_tracing_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
    processor: str,
    expected: TraceExporter,
) -> None:
    """
    Purpose: Verify the Node enable flag maps its configured span processor.
    Why this matters: Shared deployment settings must enable the intended exporter.
    Setup summary: Enable Node-compatible tracing, vary the processor, and assert its mapping.
    """
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.setenv("ENABLE_OPENTELEMETRY", "true")
    monkeypatch.setenv("OTEL_SPAN_PROCESSOR", processor)

    assert TracingSettings().exporter == expected


@pytest.mark.ai
@pytest.mark.unit
def test_resolve_exporter__defaults_to_otlp__when_node_tracing_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify enabled Node-compatible tracing defaults to OTLP.
    Why this matters: It matches the Node service default without extra configuration.
    Setup summary: Enable tracing without a processor value and assert the OTLP selection.
    """
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.setenv("ENABLE_OPENTELEMETRY", "true")
    monkeypatch.delenv("OTEL_SPAN_PROCESSOR", raising=False)

    assert TracingSettings().exporter is TraceExporter.OTLP
    assert TracingSettings.try_load() is not None


@pytest.mark.ai
@pytest.mark.unit
def test_resolve_exporter__prefers_standard_endpoint__over_node_tracing_disable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify standard endpoint settings override the Node compatibility disable flag.
    Why this matters: Standard OpenTelemetry configuration must take precedence.
    Setup summary: Disable Node-compatible tracing with an endpoint present and assert OTLP.
    """
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.setenv("ENABLE_OPENTELEMETRY", "false")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")

    assert TracingSettings().exporter is TraceExporter.OTLP
    assert TracingSettings.try_load() is not None


@pytest.mark.ai
@pytest.mark.unit
def test_resolve_exporter__prefers_standard_exporter__over_node_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify standard OpenTelemetry configuration overrides compatibility aliases.
    Why this matters: Python applications need predictable standard OTel behavior.
    Setup summary: Configure conflicting standard and Node variables and assert the standard exporter wins.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
    monkeypatch.setenv("ENABLE_OPENTELEMETRY", "false")
    monkeypatch.setenv("OTEL_SPAN_PROCESSOR", "none")

    assert TracingSettings().exporter is TraceExporter.CONSOLE
    assert TracingSettings.try_load() is not None


@pytest.mark.ai
@pytest.mark.unit
def test_resolve_exporter__uses_endpoint__when_exporter_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify an OTLP endpoint alone enables the otlp exporter.
    Why this matters: Deployments often set only the collector URL.
    Setup summary: Clear exporter flags, set an endpoint, assert otlp.
    """
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.delenv("ENABLE_OPENTELEMETRY", raising=False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")

    assert TracingSettings().exporter is TraceExporter.OTLP
    assert TracingSettings.try_load() is not None


@pytest.mark.ai
@pytest.mark.unit
def test_resolve_exporter__treats_empty_values_as_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify blank OpenTelemetry values do not enable or invalidate tracing.
    Why this matters: OpenTelemetry defines empty environment variables as unset.
    Setup summary: Set blank exporter, processor, and endpoints and assert tracing is disabled.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "")
    monkeypatch.setenv("OTEL_SPAN_PROCESSOR", "")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    monkeypatch.delenv("ENABLE_OPENTELEMETRY", raising=False)

    assert TracingSettings.try_load() is None

    monkeypatch.setenv("ENABLE_OPENTELEMETRY", "true")
    assert TracingSettings().exporter is TraceExporter.OTLP
    assert TracingSettings.try_load() is not None

    monkeypatch.setenv("ENABLE_OPENTELEMETRY", "false")
    assert TracingSettings.try_load() is None


@pytest.mark.ai
@pytest.mark.unit
def test_tracing_settings__treats_empty_service_values_as_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify blank service attributes do not block the deployment version fallback.
    Why this matters: Trace resources must not contain empty service attributes.
    Setup summary: Set blank standard service values and assert the Node version remains usable.
    """
    monkeypatch.setenv("OTEL_SERVICE_NAME", "")
    monkeypatch.setenv("OTEL_SERVICE_VERSION", "")
    monkeypatch.setenv("VERSION", "node-version")

    settings = TracingSettings()

    assert settings.service_name is None
    assert settings.service_version == "node-version"


@pytest.mark.ai
@pytest.mark.unit
def test_tracing_settings__reads_enable_opentelemetry__from_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Purpose: Verify ENABLE_OPENTELEMETRY is read from a .env file, not just os.environ.
    Why this matters: pydantic-settings does not populate os.environ from .env, so a local
    dev opt-in written only to .env would otherwise silently never enable tracing.
    Setup summary: Write the flag to a temp .env, delete it from real os.environ, assert on.
    """
    monkeypatch.delenv("ENABLE_OPENTELEMETRY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("ENABLE_OPENTELEMETRY=true\n")

    settings = TracingSettings(_env_file=str(env_file))

    assert settings.enabled is True
    assert settings.exporter is TraceExporter.OTLP


@pytest.mark.ai
@pytest.mark.unit
def test_configure_tracing__raises_install_hint__when_otel_extra_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify enabled tracing explains how to install its optional dependencies.
    Why this matters: An opaque module error would make production configuration difficult.
    Setup summary: Block OpenTelemetry imports, enable console tracing, and assert the install hint.
    """
    original_import = builtins.__import__

    def import_without_opentelemetry(
        name, globals=None, locals=None, fromlist=(), level=0
    ):
        if name.startswith("opentelemetry"):
            raise ImportError("OpenTelemetry is unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_opentelemetry)
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")

    with pytest.raises(ImportError, match=r"unique_toolkit\[otel\]"):
        configure_tracing()


@pytest.mark.ai
@pytest.mark.unit
def test_configure_tracing__raises__for_unsupported_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify unknown exporters fail fast with a clear error.
    Why this matters: Typos in env config should not silently no-op.
    Setup summary: Set an unsupported exporter name and assert ValueError.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "jaeger")

    with pytest.raises(ValueError, match="Input should be"):
        configure_tracing()


@pytest.mark.ai
@pytest.mark.unit
def test_configure_tracing__creates_valid_span_context__with_console_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify console configuration creates a provider that records spans.
    Why this matters: MCP instrumentation needs a valid active context for log correlation.
    Setup summary: Configure console tracing in-process and assert a created span is valid.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")

    assert configure_tracing(service_name="test-service") is True
    with trace.get_tracer(__name__).start_as_current_span("test-span") as span:
        assert span.get_span_context().is_valid


@pytest.mark.ai
@pytest.mark.unit
def test_configure_tracing__uses_node_version__when_standard_version_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify the Node deployment version is added to the tracing resource.
    Why this matters: Trace backends need service version parity across Node and Python services.
    Setup summary: Configure console tracing with VERSION and assert the resource attribute.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
    monkeypatch.setenv("VERSION", "node-version")
    monkeypatch.delenv("OTEL_SERVICE_VERSION", raising=False)

    assert configure_tracing() is True
    assert (
        trace.get_tracer_provider().resource.attributes["service.version"]
        == "node-version"
    )


@pytest.mark.ai
@pytest.mark.unit
def test_configure_tracing__installs_otlp_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify OTLP exporter path constructs a TracerProvider successfully.
    Why this matters: Production Alloy/OTLP is the primary export mode.
    Setup summary: Enable otlp exporter and assert configure_tracing returns True.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318")

    assert configure_tracing(service_name="otlp-service") is True
    assert not isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider)


@pytest.mark.ai
@pytest.mark.unit
@pytest.mark.asyncio
async def test_trace_context_middleware__continues_incoming_trace_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify ASGI requests create a child span of the incoming trace.
    Why this matters: MCP and Assistants Core must appear in the caller's distributed trace.
    Setup summary: Send a traceparent through middleware and assert its trace ID.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
    assert configure_tracing() is True

    trace_id = "1234567890abcdef1234567890abcdef"
    parent_span_id = "1234567890abcdef"
    seen: dict[str, str] = {}

    async def app(scope, receive, send):
        span_context = trace.get_current_span().get_span_context()
        seen["trace_id"] = format(span_context.trace_id, "032x")
        seen["span_id"] = format(span_context.span_id, "016x")

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        return None

    middleware = TraceContextMiddleware(app, span_name="test-request")
    await middleware(
        {
            "type": "http",
            "headers": [
                (b"traceparent", f"00-{trace_id}-{parent_span_id}-01".encode())
            ],
        },
        receive,
        send,
    )

    assert seen["trace_id"] == trace_id
    assert seen["span_id"] != parent_span_id


@pytest.mark.ai
@pytest.mark.unit
@pytest.mark.asyncio
async def test_trace_context_middleware__passes_through_non_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify non-HTTP ASGI scopes skip span creation.
    Why this matters: Lifespan/websocket must not require trace headers.
    Setup summary: Invoke middleware with a lifespan scope and assert the app runs.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
    assert configure_tracing() is True
    called = False

    async def app(scope, receive, send):
        nonlocal called
        called = True

    await TraceContextMiddleware(app)({"type": "lifespan"}, None, None)
    assert called is True


@pytest.mark.ai
@pytest.mark.unit
@pytest.mark.asyncio
async def test_trace_context_middleware__combines_repeated_tracestate_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify ASGI middleware preserves every incoming tracestate entry.
    Why this matters: Dropping vendor state can change downstream trace sampling decisions.
    Setup summary: Send repeated tracestate headers and assert the active context preserves both.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
    assert configure_tracing() is True
    seen: dict[str, str] = {}

    async def app(scope, receive, send):
        seen["state"] = (
            trace.get_current_span().get_span_context().trace_state.to_header()
        )

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        return None

    await TraceContextMiddleware(app)(
        {
            "type": "http",
            "headers": [
                (
                    b"traceparent",
                    b"00-1234567890abcdef1234567890abcdef-1234567890abcdef-01",
                ),
                (b"tracestate", b"foo=bar"),
                (b"tracestate", b"bar=baz"),
            ],
        },
        receive,
        send,
    )

    assert seen["state"] == "foo=bar,bar=baz"


@pytest.mark.ai
@pytest.mark.unit
def test_inject_trace_headers__adds_active_w3c_trace_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify outgoing requests receive the active trace context.
    Why this matters: Downstream Node services need a parent trace to continue correlation.
    Setup summary: Start a span, inject headers, and assert its trace ID is present.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
    assert configure_tracing() is True

    with trace.get_tracer(__name__).start_as_current_span("source") as span:
        headers: dict[str, str] = {}
        inject_trace_headers(headers)
        assert headers["traceparent"].split("-")[1] == format(
            span.get_span_context().trace_id, "032x"
        )


@pytest.mark.ai
@pytest.mark.unit
def test_configure_tracing__does_not_replace_provider__when_called_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify repeated setup does not replace the global trace provider.
    Why this matters: Process startup paths may configure tracing more than once.
    Setup summary: Configure console tracing twice and assert provider identity remains.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")

    assert configure_tracing() is True
    provider = trace.get_tracer_provider()
    assert configure_tracing() is True
    assert trace.get_tracer_provider() is provider


@pytest.mark.ai
@pytest.mark.unit
def test_configure_tracing__does_not_replace_an_existing_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify tracing preserves SDK configuration installed before toolkit startup.
    Why this matters: Applications may initialize OpenTelemetry outside this bootstrap.
    Setup summary: Install a provider, configure tracing, and assert its identity remains.
    """
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
    provider = TracerProvider()
    trace.set_tracer_provider(provider)

    assert configure_tracing() is True
    assert trace.get_tracer_provider() is provider


@pytest.mark.ai
@pytest.mark.unit
def test_instrument_fastapi_app__raises_fastapi_install_hint__when_fastapi_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify a missing fastapi package is attributed to the fastapi extra, not otel.
    Why this matters: opentelemetry-instrumentation-fastapi imports fastapi internally, so
    its own ImportError would otherwise be misreported as a missing otel extra.
    Setup summary: Block the fastapi import and assert the fastapi-specific install hint.
    """
    pytest.importorskip("fastapi")
    from fastapi import FastAPI

    app = FastAPI()
    original_import = builtins.__import__

    def import_without_fastapi(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "fastapi":
            raise ImportError("fastapi is unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_fastapi)

    with pytest.raises(ImportError, match=r"unique_toolkit\[fastapi\]"):
        instrument_fastapi_app(app)


@pytest.mark.ai
@pytest.mark.unit
def test_instrument_fastapi_app__raises_otel_install_hint__when_otel_extra_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify the FastAPI helper explains how to install its optional dependency.
    Why this matters: An opaque ImportError would make onboarding a new service harder.
    Setup summary: Block the fastapi instrumentation import and assert the install hint.
    """
    pytest.importorskip("fastapi")
    from fastapi import FastAPI

    original_import = builtins.__import__

    def import_without_fastapi_instrumentation(
        name, globals=None, locals=None, fromlist=(), level=0
    ):
        if name == "opentelemetry.instrumentation.fastapi":
            raise ImportError("instrumentation package is unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_fastapi_instrumentation)

    with pytest.raises(ImportError, match=r"unique_toolkit\[otel\]"):
        instrument_fastapi_app(FastAPI())


@pytest.mark.ai
@pytest.mark.unit
def test_instrument_fastapi_app__traces_inbound_requests() -> None:
    """
    Purpose: Verify an instrumented app produces a valid server span for inbound requests.
    Why this matters: This is what joins assistants-core's spans to a caller's trace.
    Setup summary: Instrument a FastAPI app, call it via TestClient, assert a recorded span.
    """
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    app = FastAPI()

    @app.get("/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    instrument_fastapi_app(app, excluded_urls="/metrics")

    response = TestClient(app).get("/ping")

    assert response.status_code == 200
    assert any(span.name.endswith("/ping") for span in exporter.get_finished_spans())


@pytest.mark.ai
@pytest.mark.unit
def test_instrument_fastapi_app__excludes_urls_matching_excluded_urls() -> None:
    """
    Purpose: Verify excluded_urls actually suppresses spans for the matching route.
    Why this matters: This is what keeps polled routes like /metrics out of every trace.
    Setup summary: Instrument with excluded_urls, call both routes, assert only one traced.
    """
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    app = FastAPI()

    @app.get("/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/metrics")
    def metrics() -> dict[str, bool]:
        return {"metrics": True}

    instrument_fastapi_app(app, excluded_urls="/metrics")

    client = TestClient(app)
    client.get("/ping")
    client.get("/metrics")

    span_names = [span.name for span in exporter.get_finished_spans()]
    assert any(name.endswith("/ping") for name in span_names)
    assert not any(name.endswith("/metrics") for name in span_names)


@pytest.mark.ai
@pytest.mark.unit
def test_instrument_fastapi_app__is_idempotent() -> None:
    """
    Purpose: Verify calling the FastAPI helper twice on the same app does not raise.
    Why this matters: Process startup paths may configure tracing more than once.
    Setup summary: Instrument the same app twice and assert one span per request.
    """
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    app = FastAPI()

    @app.get("/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    instrument_fastapi_app(app)
    instrument_fastapi_app(app)

    TestClient(app).get("/ping")

    route_spans = [s for s in exporter.get_finished_spans() if s.name == "GET /ping"]
    assert len(route_spans) == 1


@pytest.mark.ai
@pytest.mark.unit
def test_instrument_requests__raises_install_hint__when_otel_extra_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify the requests helper explains how to install its optional dependency.
    Why this matters: An opaque ImportError would make onboarding a new service harder.
    Setup summary: Block the requests instrumentation import and assert the install hint.
    """
    original_import = builtins.__import__

    def import_without_requests_instrumentation(
        name, globals=None, locals=None, fromlist=(), level=0
    ):
        if name == "opentelemetry.instrumentation.requests":
            raise ImportError("instrumentation package is unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", import_without_requests_instrumentation)

    with pytest.raises(ImportError, match=r"unique_toolkit\[otel\]"):
        instrument_requests()


@pytest.mark.ai
@pytest.mark.unit
def test_instrument_requests__is_idempotent() -> None:
    """
    Purpose: Verify calling the requests helper twice does not raise.
    Why this matters: Process startup paths may configure tracing more than once.
    Setup summary: Instrument requests twice and assert no exception, then uninstrument.
    """
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    instrument_requests()
    try:
        instrument_requests()
        assert RequestsInstrumentor().is_instrumented_by_opentelemetry is True
    finally:
        RequestsInstrumentor().uninstrument()
