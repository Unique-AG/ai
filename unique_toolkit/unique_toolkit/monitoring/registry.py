from __future__ import annotations

import asyncio
import functools
import time
from contextlib import contextmanager
from typing import Callable

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()


def get_metrics() -> bytes:
    """Returns all registered metrics in Prometheus text format."""
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

    def histogram(self, name: str, description: str, labels: list[str]) -> Histogram:
        return Histogram(
            f"{self._prefix}_{name}", description, labels, registry=REGISTRY
        )

    def counter(self, name: str, description: str, labels: list[str]) -> Counter:
        return Counter(f"{self._prefix}_{name}", description, labels, registry=REGISTRY)

    def gauge(self, name: str, description: str, labels: list[str]) -> Gauge:
        return Gauge(f"{self._prefix}_{name}", description, labels, registry=REGISTRY)


@contextmanager
def track(duration: Histogram, errors: Counter | None = None, **labels):
    """Context manager that auto-times a block and records metrics.

    Use when labels are dynamic (determined at runtime).

    Example — search engine with dynamic engine label::

        with track(search_duration, search_errors, engine=self.engine_name):
            results = await self._execute_search(query)

    Example — LLM call with purpose label::

        with track(llm_duration, llm_errors, purpose="snippet_judge"):
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
) -> Callable:
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
            with track(duration, errors, **labels):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with track(duration, errors, **labels):
                return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
