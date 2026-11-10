"""Prometheus metrics for the Activity Records outbox."""

from __future__ import annotations

from dataclasses import dataclass, fields
from functools import cache
from typing import Final, Literal, get_args

from unique_toolkit.experimental.resources.activity_records.config import (
    ACTIVITY_RECORDS_INSTALL_HINT,
    DEFAULT_ACTIVITY_EVENTS_METRIC_NAME,
)

try:
    from prometheus_client import (  # pyright: ignore[reportMissingImports]
        CollectorRegistry,
        Counter,
        Gauge,
    )

    from unique_toolkit.monitoring import REGISTRY, MetricNamespace
except ImportError as error:  # pragma: no cover
    raise ImportError(
        "The Activity Records metrics need prometheus_client. "
        f"{ACTIVITY_RECORDS_INSTALL_HINT}"
    ) from error

PublishFailureReason = Literal["timeout", "rejected"]
PUBLISH_FAILURE_REASONS: Final = get_args(PublishFailureReason)


@dataclass(frozen=True, slots=True)
class _FixedOutboxMetrics:
    record_failures: Counter
    publish_failures: Counter
    backoff_max_reached: Counter
    discarded: Counter
    invalid_events: Counter
    flag_check_failures: Counter
    pending_rows: Gauge
    oldest_pending_age_seconds: Gauge
    rows_at_max_backoff: Gauge


@dataclass(frozen=True, slots=True)
class ActivityEventOutboxMetrics(_FixedOutboxMetrics):
    events: Counter


# The three gauges are table-wide: every worker reports the same value, so livemax keeps one series.
@cache
def _create_fixed_outbox_metrics(registry: CollectorRegistry) -> _FixedOutboxMetrics:
    outbox_metrics = MetricNamespace(
        "unique_activity_event_outbox",
        registry=registry,
    )
    publish_failures = outbox_metrics.counter(
        "publish_failures_total",
        "Activity event outbox publishes not confirmed by the broker",
        ["reason"],
    )
    for reason in PUBLISH_FAILURE_REASONS:
        publish_failures.labels(reason=reason).inc(0)

    return _FixedOutboxMetrics(
        record_failures=outbox_metrics.counter(
            "record_failures_total",
            "Activity events lost because a best-effort record failed",
            [],
        ),
        publish_failures=publish_failures,
        backoff_max_reached=outbox_metrics.counter(
            "backoff_max_reached_total",
            "Activity events whose retry delay reached the backoff cap",
            [],
        ),
        discarded=outbox_metrics.counter(
            "discarded_total",
            "Activity events discarded because the company flag was off",
            [],
        ),
        invalid_events=outbox_metrics.counter(
            "invalid_events_total",
            "Publish attempts containing invalid activity events",
            [],
        ),
        flag_check_failures=outbox_metrics.counter(
            "flag_check_failures_total",
            "Activity records flag checks that failed or timed out",
            [],
        ),
        pending_rows=outbox_metrics.gauge(
            "pending_rows",
            "Activity events waiting in the outbox, capped at 100000",
            [],
            multiprocess_mode="livemax",
        ),
        oldest_pending_age_seconds=outbox_metrics.gauge(
            "oldest_pending_age_seconds",
            "Age of the oldest activity event waiting in the outbox",
            [],
            multiprocess_mode="livemax",
        ),
        rows_at_max_backoff=outbox_metrics.gauge(
            "rows_at_max_backoff",
            "Activity events currently at the maximum retry backoff",
            [],
            multiprocess_mode="livemax",
        ),
    )


def get_or_create_activity_event_outbox_metrics(
    *,
    metric_name: str = DEFAULT_ACTIVITY_EVENTS_METRIC_NAME,
    registry: CollectorRegistry = REGISTRY,
) -> ActivityEventOutboxMetrics:
    """Build the metrics once per registry; only the events counter depends on the name."""
    return _create_outbox_metrics(metric_name, registry)


@cache
def _create_outbox_metrics(
    metric_name: str, registry: CollectorRegistry
) -> ActivityEventOutboxMetrics:
    fixed = _create_fixed_outbox_metrics(registry)
    events = Counter(
        metric_name,
        "Activity events by outcome, source, actor type and event type",
        labelnames=("outcome", "source", "actorType", "eventType"),
        registry=registry,
    )
    return ActivityEventOutboxMetrics(
        events=events, **{f.name: getattr(fixed, f.name) for f in fields(fixed)}
    )
