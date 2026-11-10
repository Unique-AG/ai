from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

prometheus_client = pytest.importorskip(
    "prometheus_client",
    reason="Activity Records metrics tests need the activity-records extra",
)

from prometheus_client import CollectorRegistry  # noqa: E402

from unique_toolkit.experimental.resources.activity_records.config import (  # noqa: E402
    DEFAULT_ACTIVITY_EVENTS_METRIC_NAME,
)
from unique_toolkit.experimental.resources.activity_records.metrics import (  # noqa: E402
    get_or_create_activity_event_outbox_metrics,
)
from unique_toolkit.monitoring import REGISTRY  # noqa: E402

pytestmark = pytest.mark.ai


def test_publish_failure_reasons_are_zero_initialised_and_use_the_toolkit_registry() -> (
    None
):
    registry = CollectorRegistry()
    get_or_create_activity_event_outbox_metrics(registry=registry)

    for reason in ("timeout", "rejected"):
        assert (
            registry.get_sample_value(
                "unique_activity_event_outbox_publish_failures_total",
                {"reason": reason},
            )
            == 0
        )

    default = get_or_create_activity_event_outbox_metrics()
    default.pending_rows.set(3)
    assert REGISTRY.get_sample_value("unique_activity_event_outbox_pending_rows") == 3


def test_event_counter_uses_the_node_labels() -> None:
    registry = CollectorRegistry()
    metrics = get_or_create_activity_event_outbox_metrics(registry=registry)

    metrics.events.labels(
        outcome="sent",
        source="web-search",
        actorType="user",
        eventType="web-search.tool.called",
    ).inc(2)

    assert (
        registry.get_sample_value(
            "unique_activity_events_total",
            {
                "outcome": "sent",
                "source": "web-search",
                "actorType": "user",
                "eventType": "web-search.tool.called",
            },
        )
        == 2
    )


def test_a_second_metric_name_gets_its_own_events_counter() -> None:
    registry = CollectorRegistry()
    first = get_or_create_activity_event_outbox_metrics(registry=registry)
    second = get_or_create_activity_event_outbox_metrics(
        metric_name="other_events_total", registry=registry
    )

    labels = {
        "outcome": "sent",
        "source": "web-search",
        "actorType": "user",
        "eventType": "web-search.tool.called",
    }
    second.events.labels(**labels).inc()

    assert registry.get_sample_value("other_events_total", labels) == 1
    assert registry.get_sample_value("unique_activity_events_total", labels) is None
    assert second.publish_failures is first.publish_failures


def test_defaults_and_explicit_values_share_one_set_of_metrics() -> None:
    registry = CollectorRegistry()

    implicit = get_or_create_activity_event_outbox_metrics(registry=registry)
    explicit = get_or_create_activity_event_outbox_metrics(
        metric_name=DEFAULT_ACTIVITY_EVENTS_METRIC_NAME, registry=registry
    )

    assert explicit is implicit


def test_table_wide_gauges_use_the_livemax_multiprocess_mode(tmp_path: Path) -> None:
    code = """
from prometheus_client import CollectorRegistry
from unique_toolkit.experimental.resources.activity_records.metrics import (
    get_or_create_activity_event_outbox_metrics,
)

metrics = get_or_create_activity_event_outbox_metrics(registry=CollectorRegistry())
metrics.pending_rows.set(3)
metrics.oldest_pending_age_seconds.set(2)
metrics.rows_at_max_backoff.set(1)
"""
    subprocess.run(
        [sys.executable, "-I", "-c", code],
        env={**os.environ, "PROMETHEUS_MULTIPROC_DIR": str(tmp_path)},
        check=True,
    )

    modes = {p.name.split("_")[1] for p in tmp_path.glob("gauge_*.db")}
    assert modes == {"livemax"}
