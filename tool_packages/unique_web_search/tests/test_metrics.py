"""Tests for unique_web_search Prometheus metrics wiring."""

import pytest
from prometheus_client import Counter, Histogram
from unique_toolkit.monitoring import get_metrics, metric_scope

from unique_web_search import metrics as metrics_module


@pytest.mark.ai
def test_metrics__exports_histograms_and_counters__for_instrumented_paths() -> None:
    """
    Purpose: Verify each declared metric is a Prometheus Histogram or Counter with the expected prefix.
    Why this matters: Broken imports or optional-dep gaps would fail at runtime in executors and the tool.
    Setup summary: Import the metrics module and assert types on representative instruments.
    """
    assert isinstance(metrics_module.search_duration, Histogram)
    assert isinstance(metrics_module.search_errors, Counter)
    assert isinstance(metrics_module.tool_duration, Histogram)
    assert isinstance(metrics_module.tool_errors, Counter)
    assert isinstance(metrics_module.llm_duration, Histogram)
    assert isinstance(metrics_module.llm_errors, Counter)
    assert isinstance(metrics_module.crawl_duration, Histogram)
    assert isinstance(metrics_module.crawl_errors, Counter)


@pytest.mark.ai
def test_metrics__metric_scope__observes_duration_and_exposes_metrics() -> None:
    """
    Purpose: Confirm `metric_scope` works with package histograms/counters and metrics appear in exposition.
    Why this matters: Executors rely on this context manager; a label mismatch would raise at runtime.
    Setup summary: Run a no-op block under metric_scope with test labels, then scan get_metrics() output.
    """
    with metric_scope(
        metrics_module.search_duration,
        metrics_module.search_errors,
        engine="pytest_metrics",
    ):
        pass

    body = get_metrics()
    assert b"unique_web_search_search_duration_seconds" in body


@pytest.mark.ai
def test_metrics__metric_scope_llm_errors_on_exception__records_error_type_label() -> (
    None
):
    """
    Purpose: Ensure `llm_errors` declares `error_type` so `metric_scope` can increment on failure.
    Why this matters: A label mismatch raises `ValueError` from prometheus_client and hides the real error.
    Setup summary: Raise inside `metric_scope` with `llm_errors`; assert exposition includes purpose and exception type.
    """
    with pytest.raises(RuntimeError, match="expected failure"):
        with metric_scope(
            metrics_module.llm_duration,
            metrics_module.llm_errors,
            purpose="pytest_llm_errors",
        ):
            raise RuntimeError("expected failure")

    body = get_metrics()
    assert b"unique_web_search_llm_errors_total" in body
    assert b"pytest_llm_errors" in body
    assert b"RuntimeError" in body
