from __future__ import annotations

from unique_toolkit.monitoring import MetricNamespace

m = MetricNamespace("unique_search_proxy")

search_duration_seconds = m.histogram(
    "search_duration_seconds",
    "Search request latency",
    ["engine"],
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

crawl_blocked_total = m.counter(
    "crawl_blocked_total",
    "Crawl targets blocked by URL safety policy",
    ["reason_category"],
)

proxy_errors_total = m.counter(
    "proxy_errors_total",
    "Top-level API errors returned to clients",
    ["error_code"],
)


def _metrics_enabled() -> bool:
    from unique_search_proxy.web.monitoring.settings import prometheus_settings

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


def record_crawl_blocked(reason_category: str, count: int = 1) -> None:
    if not _metrics_enabled():
        return
    crawl_blocked_total.labels(reason_category=reason_category).inc(count)


def record_proxy_error(error_code: str) -> None:
    if not _metrics_enabled():
        return
    proxy_errors_total.labels(error_code=error_code).inc()
