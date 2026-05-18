"""Tests for multiprocess mode in unique_toolkit.monitoring.registry."""

import multiprocessing
import os

import pytest

pytest.importorskip("prometheus_client")

from unique_toolkit.monitoring.registry import get_metrics  # noqa: E402

# ---------------------------------------------------------------------------
# Worker helper — must be module-level so multiprocessing.spawn can pickle it
# ---------------------------------------------------------------------------


def _worker_write_http_histogram(tmp_dir: str, pid: int) -> None:
    """Simulate a worker writing HTTP histogram metrics under a fake PID."""
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = tmp_dir

    from prometheus_client import CollectorRegistry, Histogram, values

    values.ValueClass = values.MultiProcessValue(lambda: pid)
    registry = CollectorRegistry()
    h = Histogram(
        "python_http_request_duration_seconds",
        "HTTP request duration",
        ["method", "path"],
        registry=registry,
    )
    h.labels(method="GET", path="/api/test").observe(0.05)


def _worker_write_counter(tmp_dir: str, pid: int, count: int) -> None:
    """Simulate a Gunicorn worker: write `count` increments under a fake PID."""
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = tmp_dir

    from prometheus_client import CollectorRegistry, Counter, values

    values.ValueClass = values.MultiProcessValue(lambda: pid)

    registry = CollectorRegistry()
    c = Counter(
        "test_multiprocess_requests_total",
        "Test counter for multiprocess aggregation",
        ["method"],
        registry=registry,
    )
    for _ in range(count):
        c.labels(method="GET").inc()


# ---------------------------------------------------------------------------
# Two-PID aggregation
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_get_metrics__multiprocess__sums_two_worker_pids(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Purpose: Verify get_metrics() aggregates per-PID .db files from two simulated workers.
    Why this matters: Without MultiProcessCollector, scrapes return only one worker's view —
    the root cause of the sawtooth counter pattern described in UN-19849.
    Setup summary: Spawn two worker processes each writing to the same PROMETHEUS_MULTIPROC_DIR
    under distinct fake PIDs, then call get_metrics() and assert the total equals the sum.
    """
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))

    ctx = multiprocessing.get_context("spawn")

    # Worker A writes 3 requests; worker B writes 5 requests.
    p1 = ctx.Process(target=_worker_write_counter, args=(str(tmp_path), 1001, 3))
    p2 = ctx.Process(target=_worker_write_counter, args=(str(tmp_path), 1002, 5))
    p1.start()
    p2.start()
    p1.join()
    p2.join()

    assert p1.exitcode == 0, f"Worker 1 failed with exit code {p1.exitcode}"
    assert p2.exitcode == 0, f"Worker 2 failed with exit code {p2.exitcode}"

    # The test process imported prometheus_client before PROMETHEUS_MULTIPROC_DIR was set,
    # so get_metrics() correctly warns about the import-order violation. We acknowledge it
    # explicitly here so it doesn't leak as an uncaught warning in CI output.
    with pytest.warns(RuntimeWarning, match="imported before the env var"):
        output = get_metrics().decode()

    assert "test_multiprocess_requests_total" in output
    # Prometheus text format: name{labels} value — the total line is the _total suffix
    assert 'test_multiprocess_requests_total{method="GET"} 8.0' in output


@pytest.mark.ai
def test_get_metrics__multiprocess__contains_python_http_metric_name(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Purpose: Verify get_metrics() output contains the renamed python_http_* family.
    Why this matters: Dashboards and alerts query python_http_request_duration_seconds_*;
    the old unprefixed name must not appear in the output.
    Setup summary: Use monkeypatched PROMETHEUS_MULTIPROC_DIR to activate multiprocess path,
    then check that get_metrics() mentions the new metric family name (from files on disk).
    """
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))

    ctx = multiprocessing.get_context("spawn")

    p = ctx.Process(target=_worker_write_http_histogram, args=(str(tmp_path), 2001))
    p.start()
    p.join()
    assert p.exitcode == 0

    # Same import-order caveat as the aggregation test above — acknowledge the warning.
    with pytest.warns(RuntimeWarning, match="imported before the env var"):
        output = get_metrics().decode()

    assert "python_http_request_duration_seconds" in output
    assert "http_request_duration_seconds" not in output.replace(
        "python_http_request_duration_seconds", ""
    )


# ---------------------------------------------------------------------------
# Import-order warning
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_get_metrics__warns__when_env_var_set_after_import(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Purpose: Verify get_metrics() emits a RuntimeWarning when PROMETHEUS_MULTIPROC_DIR is set
    after prometheus_client was already imported (import-order violation).
    Why this matters: Silent misconfiguration causes the sawtooth bug to persist even with
    the multiprocess flag set. The warning surfaces the problem during development.
    Setup summary: Set env var after import (the test process already imported prometheus_client),
    call get_metrics(), assert a RuntimeWarning containing the key phrase is raised.
    """
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))

    with pytest.warns(RuntimeWarning, match="imported before the env var"):
        get_metrics()
