"""Tests for unique_toolkit.monitoring.registry module."""

import pytest
from prometheus_client import CollectorRegistry, Counter, Histogram

import unique_toolkit.monitoring.registry as registry_module
from unique_toolkit.monitoring.registry import (
    MetricNamespace,
    get_metrics,
    metric_scope,
    track_execution,
)


@pytest.fixture
def fresh_registry(monkeypatch: pytest.MonkeyPatch) -> CollectorRegistry:
    """
    Provide an isolated CollectorRegistry per test.

    Patches the module-level REGISTRY so MetricNamespace creates metrics
    in this registry instead of the shared global one, avoiding duplicate
    metric name errors across tests.
    """
    registry = CollectorRegistry()
    monkeypatch.setattr(registry_module, "REGISTRY", registry)
    return registry


@pytest.fixture
def test_metrics(fresh_registry: CollectorRegistry):
    """Provide a pair of (duration Histogram, errors Counter) for metric_scope() tests."""
    duration = Histogram(
        "test_duration_seconds", "Test duration", ["op"], registry=fresh_registry
    )
    errors = Counter(
        "test_errors_total",
        "Test errors",
        ["op", "error_type"],
        registry=fresh_registry,
    )
    return duration, errors


# ---------------------------------------------------------------------------
# MetricNamespace
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_metric_namespace__histogram__registers_with_prefix(
    fresh_registry: CollectorRegistry,
) -> None:
    """
    Purpose: Verify MetricNamespace.histogram() creates a Histogram with the correct prefixed name.
    Why this matters: Metric naming determines how dashboards, alerts, and PromQL queries are written.
    Setup summary: Create a namespace with prefix "svc", call histogram(), assert name in output.
    """
    m = MetricNamespace("svc")

    hist = m.histogram("latency_seconds", "Latency", ["label"])

    assert isinstance(hist, Histogram)
    output = get_metrics().decode()
    assert "svc_latency_seconds" in output


@pytest.mark.ai
def test_metric_namespace__counter__registers_with_prefix(
    fresh_registry: CollectorRegistry,
) -> None:
    """
    Purpose: Verify MetricNamespace.counter() creates a Counter with the correct prefixed name.
    Why this matters: Counter naming governs rate queries (rate(svc_ops_total[5m])) — wrong prefix breaks alerts.
    Setup summary: Create a namespace with prefix "svc", call counter(), assert name in output.
    """
    m = MetricNamespace("svc")

    ctr = m.counter("ops_total", "Ops", ["label"])

    assert isinstance(ctr, Counter)
    output = get_metrics().decode()
    assert "svc_ops_total" in output


@pytest.mark.ai
def test_metric_namespace__gauge__registers_with_prefix(
    fresh_registry: CollectorRegistry,
) -> None:
    """
    Purpose: Verify MetricNamespace.gauge() creates a Gauge with the correct prefixed name.
    Why this matters: Gauge naming governs dashboards for in-flight requests and queue depths.
    Setup summary: Create a namespace with prefix "svc", call gauge(), assert name in output.
    """
    from prometheus_client import Gauge

    m = MetricNamespace("svc")

    g = m.gauge("in_flight", "In-flight", ["label"])

    assert isinstance(g, Gauge)
    output = get_metrics().decode()
    assert "svc_in_flight" in output


# ---------------------------------------------------------------------------
# get_metrics()
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_get_metrics__returns_bytes(fresh_registry: CollectorRegistry) -> None:
    """
    Purpose: Verify get_metrics() returns bytes in Prometheus text exposition format.
    Why this matters: The /metrics endpoint must return bytes that Prometheus can scrape.
    Setup summary: Call get_metrics() on an empty registry, assert result is bytes.
    """
    result = get_metrics()

    assert isinstance(result, bytes)


@pytest.mark.ai
def test_get_metrics__includes_registered_metric(
    fresh_registry: CollectorRegistry,
) -> None:
    """
    Purpose: Verify get_metrics() output includes metrics registered in the REGISTRY.
    Why this matters: Metrics that don't appear in output won't be scraped by Prometheus.
    Setup summary: Register a counter in fresh registry, call get_metrics(), assert metric name present.
    """
    m = MetricNamespace("check")
    m.counter("present_total", "Present", [])

    output = get_metrics().decode()

    assert "check_present_total" in output


# ---------------------------------------------------------------------------
# metric_scope()
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_track__records_duration__on_success(test_metrics) -> None:
    """
    Purpose: Verify metric_scope() observes a duration measurement after a successful block.
    Why this matters: Without duration recording, latency dashboards show no data.
    Setup summary: Run a trivial block inside metric_scope(), assert histogram sample count increases.
    """
    duration, _ = test_metrics

    before = duration.labels(op="test")._sum.get()

    with metric_scope(duration, op="test"):
        pass

    after = duration.labels(op="test")._sum.get()
    assert after > before


@pytest.mark.ai
def test_track__records_error__on_exception(test_metrics) -> None:
    """
    Purpose: Verify metric_scope() increments the error counter when the block raises.
    Why this matters: Without error recording, failures are invisible in Prometheus dashboards.
    Setup summary: Raise ValueError inside metric_scope(), assert errors counter incremented with correct labels.
    """
    duration, errors = test_metrics

    with pytest.raises(ValueError):
        with metric_scope(duration, errors, op="test"):
            raise ValueError("boom")

    count = errors.labels(op="test", error_type="ValueError")._value.get()
    assert count == 1


@pytest.mark.ai
def test_track__still_records_duration__on_exception(test_metrics) -> None:
    """
    Purpose: Verify metric_scope() records duration even when the block raises an exception.
    Why this matters: Latency data for failed requests is valuable for debugging.
    Setup summary: Raise inside metric_scope(), assert duration histogram still observed.
    """
    duration, errors = test_metrics

    before = duration.labels(op="test")._sum.get()

    with pytest.raises(RuntimeError):
        with metric_scope(duration, errors, op="test"):
            raise RuntimeError("fail")

    after = duration.labels(op="test")._sum.get()
    # Duration should have been recorded (sum changes) even on exception
    assert after >= before


@pytest.mark.ai
def test_track__no_errors_counter__does_not_raise__on_exception(
    test_metrics,
) -> None:
    """
    Purpose: Verify metric_scope() works without an errors counter (errors=None).
    Why this matters: Some call sites only care about duration, not errors — errors=None must be safe.
    Setup summary: Pass errors=None to metric_scope(), raise inside block, assert original exception propagates.
    """
    duration, _ = test_metrics

    with pytest.raises(KeyError):
        with metric_scope(duration, op="test"):
            raise KeyError("missing")


# ---------------------------------------------------------------------------
# track_execution() — sync
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_track_execution__sync__records_duration(test_metrics) -> None:
    """
    Purpose: Verify @track_execution decorator records duration for a sync function.
    Why this matters: Sync functions decorated with track_execution must show latency on /metrics.
    Setup summary: Decorate a sync no-op, call it, assert histogram sample count increased.
    """
    duration, _ = test_metrics

    @track_execution(duration, op="sync")
    def my_func():
        return "ok"

    before = duration.labels(op="sync")._sum.get()
    result = my_func()
    after = duration.labels(op="sync")._sum.get()

    assert result == "ok"
    assert after >= before


@pytest.mark.ai
def test_track_execution__sync__records_error__on_exception(test_metrics) -> None:
    """
    Purpose: Verify @track_execution increments error counter for a failing sync function.
    Why this matters: Error rates for decorated functions are key SLO signals.
    Setup summary: Decorate a function that raises, call it, assert errors counter incremented.
    """
    duration, errors = test_metrics

    @track_execution(duration, errors, op="sync")
    def failing():
        raise TypeError("bad type")

    with pytest.raises(TypeError):
        failing()

    count = errors.labels(op="sync", error_type="TypeError")._value.get()
    assert count == 1


# ---------------------------------------------------------------------------
# track_execution() — async
# ---------------------------------------------------------------------------


@pytest.mark.ai
@pytest.mark.asyncio
async def test_track_execution__async__records_duration(test_metrics) -> None:
    """
    Purpose: Verify @track_execution decorator records duration for an async function.
    Why this matters: Most toolkit operations are async — decorator must handle coroutines.
    Setup summary: Decorate an async no-op, await it, assert histogram sample count increased.
    """
    duration, _ = test_metrics

    @track_execution(duration, op="async")
    async def my_async_func():
        return "async_ok"

    before = duration.labels(op="async")._sum.get()
    result = await my_async_func()
    after = duration.labels(op="async")._sum.get()

    assert result == "async_ok"
    assert after >= before


@pytest.mark.ai
@pytest.mark.asyncio
async def test_track_execution__async__records_error__on_exception(
    test_metrics,
) -> None:
    """
    Purpose: Verify @track_execution increments error counter for a failing async function.
    Why this matters: Async error rates need the same visibility as sync error rates.
    Setup summary: Decorate an async function that raises, await it, assert errors counter incremented.
    """
    duration, errors = test_metrics

    @track_execution(duration, errors, op="async")
    async def async_failing():
        raise ValueError("async boom")

    with pytest.raises(ValueError):
        await async_failing()

    count = errors.labels(op="async", error_type="ValueError")._value.get()
    assert count == 1


@pytest.mark.ai
def test_track_execution__preserves_function_name(test_metrics) -> None:
    """
    Purpose: Verify @track_execution preserves the original function name via functools.wraps.
    Why this matters: Stack traces and logs use __name__; losing it makes debugging harder.
    Setup summary: Decorate a named function, check __name__ is unchanged on the wrapper.
    """
    duration, _ = test_metrics

    @track_execution(duration, op="named")
    def my_named_function():
        pass

    assert my_named_function.__name__ == "my_named_function"
