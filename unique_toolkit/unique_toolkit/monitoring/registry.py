from __future__ import annotations

import asyncio
import functools
import os
import time
import warnings
from collections.abc import Sequence
from contextlib import contextmanager
from typing import Any, Callable, Literal

from prometheus_client import (  # pyright: ignore[reportMissingImports]
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()


def get_metrics() -> bytes:
    """Returns all registered metrics in Prometheus text format.

    In multiprocess mode (PROMETHEUS_MULTIPROC_DIR is set), aggregates
    per-PID .db files from all Gunicorn workers via MultiProcessCollector.
    In single-process mode, returns metrics from the in-process REGISTRY.

    NOTE: PROMETHEUS_MULTIPROC_DIR must be set in the shell/entrypoint
    *before* Python starts. Setting it from Python after prometheus_client
    has been imported has no effect — metrics will silently bypass per-PID
    files and this function will emit a warning.
    """
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        from prometheus_client import (  # pyright: ignore[reportMissingImports]
            multiprocess,
            values,
        )

        if not getattr(values.ValueClass, "_multiprocess", False):
            warnings.warn(
                "PROMETHEUS_MULTIPROC_DIR is set but prometheus_client was imported "
                "before the env var — metrics will silently bypass per-PID files. "
                "Set PROMETHEUS_MULTIPROC_DIR in the shell/entrypoint before launching Python.",
                RuntimeWarning,
                stacklevel=2,
            )

        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry)

    return generate_latest(REGISTRY)


class MetricNamespace:
    """Factory that auto-prefixes metric names and auto-registers to REGISTRY.

    Usage::

        m = MetricNamespace("unique_web_search")
        search_duration = m.histogram("search_duration_seconds", "Search API latency", ["engine"])
        search_total    = m.counter("search_total", "Search calls by engine", ["engine"])
    """

    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    def histogram(
        self,
        name: str,
        description: str,
        labels: list[str],
        buckets: Sequence[float] | None = None,
    ) -> Histogram:
        """Create a Histogram, optionally with custom bucket boundaries.

        When ``buckets`` is omitted, prometheus_client's default buckets are used
        (top finite bucket 10s). Provide explicit buckets for workloads whose
        latency regularly exceeds 10s so ``histogram_quantile`` can resolve the
        tail; observations above the largest bucket fall into the implicit +Inf
        bucket. prometheus_client appends +Inf automatically.
        """
        if buckets is None:
            return Histogram(
                f"{self._prefix}_{name}", description, labels, registry=REGISTRY
            )
        return Histogram(
            f"{self._prefix}_{name}",
            description,
            labels,
            registry=REGISTRY,
            buckets=tuple(buckets),
        )

    def counter(self, name: str, description: str, labels: list[str]) -> Counter:
        return Counter(f"{self._prefix}_{name}", description, labels, registry=REGISTRY)

    def gauge(
        self,
        name: str,
        description: str,
        labels: list[str],
        multiprocess_mode: Literal[
            "all",
            "liveall",
            "min",
            "livemin",
            "max",
            "livemax",
            "sum",
            "livesum",
            "mostrecent",
            "livemostrecent",
        ] = "all",
    ) -> Gauge:
        return Gauge(
            f"{self._prefix}_{name}",
            description,
            labels,
            registry=REGISTRY,
            multiprocess_mode=multiprocess_mode,
        )


@contextmanager
def metric_scope(duration: Histogram, errors: Counter | None = None, **labels):
    """Context manager that auto-times a block and records metrics.

    Use when labels are dynamic (determined at runtime).

    Example — search engine with dynamic engine label::

        with metric_scope(search_duration, search_errors, engine=self.engine_name):
            results = await self._execute_search(query)

    Example — LLM call with purpose label::

        with metric_scope(llm_duration, llm_errors, purpose="snippet_judge"):
            response = await lm_service.complete_async(...)
    """
    start = time.perf_counter()
    try:
        yield
    except Exception as e:
        if errors:
            errors.labels(**labels, error_type=type(e).__name__).inc()
        raise
    finally:
        duration.labels(**labels).observe(time.perf_counter() - start)


def track_execution(
    duration: Histogram,
    errors: Counter | None = None,
    **labels,
) -> Callable[..., Any]:
    """Decorator that auto-tracks duration + errors for an entire function.

    Use when labels are static (known at definition time).
    Works with both sync and async functions.

    Example — crawl with fixed crawler name::

        @track_execution(crawl_duration, crawl_errors, crawler="basic")
        async def crawl(self, urls):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with metric_scope(duration, errors, **labels):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with metric_scope(duration, errors, **labels):
                return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
