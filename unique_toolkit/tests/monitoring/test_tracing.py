"""Tests for the optional OpenTelemetry tracing bootstrap."""

import builtins
import os
import subprocess
import sys

import pytest

from unique_toolkit.monitoring import configure_tracing
from unique_toolkit.monitoring.tracing import _resolve_exporter


def _run_tracing_script(script: str, environment: dict[str, str] | None = None) -> None:
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        env=environment or (os.environ | {"OTEL_TRACES_EXPORTER": "console"}),
        text=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.ai
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
def test_configure_tracing__returns_false__without_exporter_or_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify unset tracing configuration is a no-op.
    Why this matters: OTel must stay opt-in for existing toolkit consumers.
    Setup summary: Clear exporter and endpoint variables and assert configuration is disabled.
    """
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    assert configure_tracing() is False


@pytest.mark.ai
@pytest.mark.parametrize(
    ("processor", "expected"),
    [
        ("console", "console"),
        ("none", "none"),
    ],
)
def test_resolve_exporter__maps_node_alias__when_tracing_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
    processor: str | None,
    expected: str,
) -> None:
    """
    Purpose: Verify the Node enable flag maps its configured span processor.
    Why this matters: Shared deployment settings must enable the intended exporter.
    Setup summary: Enable Node-compatible tracing, vary the processor, and assert its mapping.
    """
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.setenv("ENABLE_OPENTELEMETRY", "true")
    monkeypatch.setenv("OTEL_SPAN_PROCESSOR", processor)

    assert _resolve_exporter() == expected


@pytest.mark.ai
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

    assert _resolve_exporter() == "otlp"


@pytest.mark.ai
def test_resolve_exporter__returns_none__when_node_tracing_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify the Node disable flag prevents endpoint-based setup.
    Why this matters: Services must be able to opt out despite shared OTLP endpoint settings.
    Setup summary: Disable Node-compatible tracing with an endpoint present and assert no exporter.
    """
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.setenv("ENABLE_OPENTELEMETRY", "false")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")

    assert _resolve_exporter() is None


@pytest.mark.ai
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

    assert _resolve_exporter() == "console"


@pytest.mark.ai
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
def test_configure_tracing__creates_valid_span_context__with_console_exporter() -> None:
    """
    Purpose: Verify console configuration creates a provider that records spans.
    Why this matters: MCP instrumentation needs a valid active context for log correlation.
    Setup summary: Run configuration in an isolated process and assert a created span is valid.
    """
    script = """
from opentelemetry import trace
from unique_toolkit.monitoring import configure_tracing

assert configure_tracing(service_name="test-service") is True
with trace.get_tracer(__name__).start_as_current_span("test-span") as span:
    assert span.get_span_context().is_valid
"""

    _run_tracing_script(script)


@pytest.mark.ai
def test_configure_tracing__uses_node_version__when_standard_version_is_unset() -> None:
    """
    Purpose: Verify the Node deployment version is added to the tracing resource.
    Why this matters: Trace backends need service version parity across Node and Python services.
    Setup summary: Configure console tracing in a child process and assert its resource uses VERSION.
    """
    script = """
from opentelemetry import trace
from unique_toolkit.monitoring import configure_tracing

assert configure_tracing() is True
assert trace.get_tracer_provider().resource.attributes["service.version"] == "node-version"
"""
    environment = os.environ | {
        "OTEL_TRACES_EXPORTER": "console",
        "VERSION": "node-version",
    }
    environment.pop("OTEL_SERVICE_VERSION", None)

    _run_tracing_script(script, environment)


@pytest.mark.ai
def test_trace_context_middleware__continues_incoming_trace_context() -> None:
    """
    Purpose: Verify ASGI requests create a child span of the incoming trace.
    Why this matters: MCP and Assistants Core must appear in the caller's distributed trace.
    Setup summary: Send a traceparent through middleware in a child process and assert its trace ID.
    """
    script = """
import asyncio

from opentelemetry import trace
from unique_toolkit.monitoring import TraceContextMiddleware, configure_tracing

trace_id = "1234567890abcdef1234567890abcdef"
parent_span_id = "1234567890abcdef"

async def app(scope, receive, send):
    span_context = trace.get_current_span().get_span_context()
    assert format(span_context.trace_id, "032x") == trace_id
    assert format(span_context.span_id, "016x") != parent_span_id

async def receive():
    return {"type": "http.request"}

async def send(message):
    return None

assert configure_tracing() is True
middleware = TraceContextMiddleware(app, span_name="test-request")
asyncio.run(
    middleware(
        {
            "type": "http",
            "headers": [(b"traceparent", f"00-{trace_id}-{parent_span_id}-01".encode())],
        },
        receive,
        send,
    )
)
"""

    _run_tracing_script(script)


@pytest.mark.ai
def test_trace_context_middleware__combines_repeated_tracestate_headers() -> None:
    """
    Purpose: Verify ASGI middleware preserves every incoming tracestate entry.
    Why this matters: Dropping vendor state can change downstream trace sampling decisions.
    Setup summary: Send repeated tracestate headers and assert the active context preserves both.
    """
    script = """
import asyncio

from opentelemetry import trace
from unique_toolkit.monitoring import TraceContextMiddleware, configure_tracing

async def app(scope, receive, send):
    assert trace.get_current_span().get_span_context().trace_state.to_header() == "foo=bar,bar=baz"

async def receive():
    return {"type": "http.request"}

async def send(message):
    return None

assert configure_tracing() is True
asyncio.run(
    TraceContextMiddleware(app)(
        {
            "type": "http",
            "headers": [
                (b"traceparent", b"00-1234567890abcdef1234567890abcdef-1234567890abcdef-01"),
                (b"tracestate", b"foo=bar"),
                (b"tracestate", b"bar=baz"),
            ],
        },
        receive,
        send,
    )
)
"""

    _run_tracing_script(script)


@pytest.mark.ai
def test_inject_trace_headers__adds_active_w3c_trace_context() -> None:
    """
    Purpose: Verify outgoing requests receive the active trace context.
    Why this matters: Downstream Node services need a parent trace to continue correlation.
    Setup summary: Start a span in a child process, inject headers, and assert its trace ID is present.
    """
    script = """
from opentelemetry import trace
from unique_toolkit.monitoring import configure_tracing, inject_trace_headers

assert configure_tracing() is True
with trace.get_tracer(__name__).start_as_current_span("source") as span:
    headers = {}
    inject_trace_headers(headers)
    assert headers["traceparent"].split("-")[1] == format(
        span.get_span_context().trace_id, "032x"
    )
"""

    _run_tracing_script(script)


@pytest.mark.ai
def test_configure_tracing__does_not_replace_provider__when_called_twice() -> None:
    """
    Purpose: Verify repeated setup does not replace the global trace provider.
    Why this matters: Process startup paths may configure tracing more than once.
    Setup summary: Configure console tracing twice in an isolated process and assert identity remains.
    """
    script = """
from opentelemetry import trace
from unique_toolkit.monitoring import configure_tracing

assert configure_tracing() is True
provider = trace.get_tracer_provider()
assert configure_tracing() is True
assert trace.get_tracer_provider() is provider
"""

    _run_tracing_script(script)
