from __future__ import annotations

from collections.abc import Iterable

from unique_toolkit.monitoring import MetricNamespace

m = MetricNamespace("unique_search_proxy")


def _linear_buckets(ceiling: float, steps: int) -> tuple[float, ...]:
    """Constant-step latency buckets (seconds) up to ``ceiling`` in ``steps``.

    The range ``(0, ceiling]`` is split into ``steps`` equal buckets, yielding
    ``ceiling/steps, 2*ceiling/steps, ..., ceiling`` inclusive. Observations above
    the ceiling land in the implicit +Inf bucket prometheus_client appends;
    histogram_quantile cannot resolve past the largest finite bucket, so each
    ceiling exceeds the workload's typical timeout. Using the same ``steps`` count
    keeps resolution comparable across workloads while the ceiling adapts to range.
    """
    step = ceiling / steps
    return tuple(round(step * i, 3) for i in range(1, steps + 1))


def _exponential_buckets(start: float, ceiling: float, count: int) -> tuple[float, ...]:
    """Geometric-progression latency buckets (seconds) from ``start`` to ``ceiling``.

    Yields ``count`` upper bounds ``start, start*factor, ..., ceiling`` where the
    factor is derived so the last bucket lands exactly on ``ceiling``. Relative
    resolution is constant across the range, which suits latencies spanning several
    orders of magnitude: fine sub-second buckets at the low end without spending
    dozens of buckets to reach the ceiling. Like ``_linear_buckets``, observations
    above ``ceiling`` land in the implicit +Inf bucket and histogram_quantile
    cannot resolve past the largest finite bucket.
    """
    factor = (ceiling / start) ** (1 / (count - 1))
    return tuple(round(start * factor**i, 3) for i in range(count))


_SEARCH_LATENCY_BUCKETS = _linear_buckets(ceiling=5.0, steps=20)
_CRAWL_LATENCY_BUCKETS = _linear_buckets(ceiling=60.0, steps=20)
_AGENT_SEARCH_LATENCY_BUCKETS = _linear_buckets(ceiling=120.0, steps=20)

# One histogram covers every endpoint, from sub-second /v1/search to /v1/agent-search
# runs approaching 120s — exponential buckets keep resolution useful at both ends.
HTTP_LATENCY_BUCKETS = _exponential_buckets(start=0.05, ceiling=120.0, count=20)

search_duration_seconds = m.histogram(
    "search_duration_seconds",
    "Search request latency",
    ["engine"],
    buckets=_SEARCH_LATENCY_BUCKETS,
)
search_total = m.counter(
    "search_total",
    "Search requests by engine",
    ["engine"],
)
search_errors_total = m.counter(
    "search_errors_total",
    "Search request failures",
    ["engine", "error_code"],
)

crawl_duration_seconds = m.histogram(
    "crawl_duration_seconds",
    "Crawl request latency",
    ["crawler"],
    buckets=_CRAWL_LATENCY_BUCKETS,
)
crawl_total = m.counter(
    "crawl_total",
    "Crawl requests by crawler",
    ["crawler"],
)
crawl_errors_total = m.counter(
    "crawl_errors_total",
    "Crawl request failures",
    ["crawler", "error_code"],
)
crawl_urls_total = m.counter(
    "crawl_urls_total",
    "URLs submitted to crawl",
    ["crawler"],
)
crawl_url_outcomes_total = m.counter(
    "crawl_url_outcomes_total",
    "Per-URL crawl outcomes",
    ["crawler", "outcome", "error_code", "http_status"],
)

crawl_blocked_total = m.counter(
    "crawl_blocked_total",
    "Crawl targets blocked by URL safety policy",
    ["reason_category"],
)

agent_search_duration_seconds = m.histogram(
    "agent_search_duration_seconds",
    "Agent search request latency",
    ["engine"],
    buckets=_AGENT_SEARCH_LATENCY_BUCKETS,
)
agent_search_total = m.counter(
    "agent_search_total",
    "Agent search requests by engine",
    ["engine"],
)
agent_search_errors_total = m.counter(
    "agent_search_errors_total",
    "Agent search request failures",
    ["engine", "error_code"],
)

proxy_errors_total = m.counter(
    "proxy_errors_total",
    "Top-level API errors returned to clients",
    ["error_code"],
)


def _metrics_enabled() -> bool:
    from unique_search_proxy_client.web.settings.monitoring import prometheus_settings

    return prometheus_settings.enabled


def record_search_success(engine: str, duration_seconds: float) -> None:
    if not _metrics_enabled():
        return
    search_total.labels(engine=engine).inc()
    search_duration_seconds.labels(engine=engine).observe(duration_seconds)


def record_search_error(engine: str, error_code: str, duration_seconds: float) -> None:
    if not _metrics_enabled():
        return
    search_errors_total.labels(engine=engine, error_code=error_code).inc()
    search_duration_seconds.labels(engine=engine).observe(duration_seconds)


def record_crawl_success(crawler: str, url_count: int, duration_seconds: float) -> None:
    if not _metrics_enabled():
        return
    crawl_total.labels(crawler=crawler).inc()
    crawl_urls_total.labels(crawler=crawler).inc(url_count)
    crawl_duration_seconds.labels(crawler=crawler).observe(duration_seconds)


def record_crawl_error(crawler: str, error_code: str, duration_seconds: float) -> None:
    if not _metrics_enabled():
        return
    crawl_errors_total.labels(crawler=crawler, error_code=error_code).inc()
    crawl_duration_seconds.labels(crawler=crawler).observe(duration_seconds)


def record_crawl_url_outcomes(
    crawler: str,
    outcomes: Iterable[tuple[str, str, str]],
) -> None:
    """Record per-URL crawl outcomes.

    Each item is an ``(outcome, error_code, http_status)`` triple where
    ``outcome`` is ``"success"`` or ``"error"``, ``error_code`` is ``""`` on
    success or the per-URL :class:`PerUrlError` code otherwise, and
    ``http_status`` is the upstream HTTP status (e.g. ``"403"``) when the failure
    was an HTTP error or ``""`` when no HTTP response was received.
    """
    if not _metrics_enabled():
        return
    for outcome, error_code, http_status in outcomes:
        crawl_url_outcomes_total.labels(
            crawler=crawler,
            outcome=outcome,
            error_code=error_code,
            http_status=http_status,
        ).inc()


def record_crawl_blocked(reason_category: str, count: int = 1) -> None:
    if not _metrics_enabled():
        return
    crawl_blocked_total.labels(reason_category=reason_category).inc(count)


def record_agent_search_success(engine: str, duration_seconds: float) -> None:
    if not _metrics_enabled():
        return
    agent_search_total.labels(engine=engine).inc()
    agent_search_duration_seconds.labels(engine=engine).observe(duration_seconds)


def record_agent_search_error(
    engine: str,
    error_code: str,
    duration_seconds: float,
) -> None:
    if not _metrics_enabled():
        return
    agent_search_errors_total.labels(engine=engine, error_code=error_code).inc()
    agent_search_duration_seconds.labels(engine=engine).observe(duration_seconds)


def record_proxy_error(error_code: str) -> None:
    if not _metrics_enabled():
        return
    proxy_errors_total.labels(error_code=error_code).inc()
