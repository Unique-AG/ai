from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from importlib import import_module
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from unique_toolkit.experimental.resources.activity_records.config import (
    FEATURE_FLAG_ENABLE_ACTIVITY_RECORDS_EVENTS_UN_22616,
)
from unique_toolkit.experimental.resources.activity_records.relay import (
    OUTBOX_RELAY_TIMINGS,
    OutboxRelay,
)
from unique_toolkit.experimental.resources.activity_records.schemas import (
    ActivityActor,
    ActivityCloudEvent,
    ActivityEventData,
)
from unique_toolkit.experimental.resources.feature_flags.schemas import FlagEvaluation

from .conftest import Metrics

relay_module = import_module(
    "unique_toolkit.experimental.resources.activity_records.relay"
)

pytestmark = pytest.mark.ai


@dataclass
class Row:
    id: str
    company_id: str
    payload: dict[str, Any]
    attempts: int = 0
    source: str = "test-source"


class Store:
    def __init__(self, rows: list[Row], schema_ok: bool = True) -> None:
        self.rows = rows
        self.schema_ok = schema_ok
        self.claimed: set[str] = set()
        self.defer_calls: list[tuple[list[str], int]] = []
        self.backoff_calls: list[list[str]] = []
        self.last_errors: list[str] = []
        self.delete_calls: list[list[str]] = []
        self.drop_deleted_ids: set[str] = set()
        self.stats_value = (0, 0.0, 0)
        self.claim_calls = 0
        self.claim_errors: list[BaseException] = []

    async def has_expected_columns(self) -> bool:
        return self.schema_ok

    async def claim(self, _token: str, limit: int, _lease: int) -> list[Row]:
        self.claim_calls += 1
        if self.claim_errors:
            raise self.claim_errors.pop(0)
        available = [row for row in self.rows if row.id not in self.claimed][:limit]
        self.claimed.update(row.id for row in available)
        return available

    async def delete_claimed(self, _token: str, ids: list[str]) -> list[str]:
        deleted = [
            row_id
            for row_id in ids
            if row_id in self.claimed and row_id not in self.drop_deleted_ids
        ]
        self.delete_calls.append(deleted)
        self.rows[:] = [row for row in self.rows if row.id not in deleted]
        self.claimed.difference_update(deleted)
        return deleted

    async def defer(self, _token: str, ids: list[str], delay: int) -> int:
        self.defer_calls.append((list(ids), delay))
        self.claimed.difference_update(ids)
        return len(ids)

    async def reschedule_with_backoff(
        self, _token: str, ids: list[str], last_error: str
    ) -> list[int]:
        self.backoff_calls.append(list(ids))
        self.last_errors.append(last_error)
        values = []
        for row in self.rows:
            if row.id in ids:
                row.attempts += 1
                values.append(row.attempts)
                self.claimed.discard(row.id)
        return values

    async def stats(self) -> Any:
        from types import SimpleNamespace

        pending, oldest, at_max = self.stats_value
        return SimpleNamespace(
            pending_rows=pending,
            oldest_pending_age_seconds=oldest,
            rows_at_max_backoff=at_max,
        )


class Flags:
    def __init__(self, values: dict[str, Any]) -> None:
        self.values = values
        self.calls: list[tuple[str, str]] = []

    async def evaluate(self, flag: str, *, company_id: str) -> FlagEvaluation:
        assert flag == FEATURE_FLAG_ENABLE_ACTIVITY_RECORDS_EVENTS_UN_22616
        self.calls.append((flag, company_id))
        value = self.values[company_id]
        if isinstance(value, BaseException):
            raise value
        if callable(value):
            value = value()
        if isinstance(value, BaseException):
            raise value
        return value


class Publisher:
    def __init__(self, actions: list[str] | None = None) -> None:
        self.actions = actions or []
        self.calls: list[list[dict[str, Any]]] = []

    async def publish(self, events: list[dict[str, Any]]) -> None:
        self.calls.append(events)
        if self.actions:
            action = self.actions.pop(0)
            if action == "timeout":
                raise TimeoutError("secret payload")
            if action == "reject":
                raise RuntimeError("secret payload")


def payload(company: str, event_id: str | None = None) -> dict[str, Any]:
    event = ActivityCloudEvent(
        id=uuid4() if event_id is None else event_id,
        source="svc",
        type="activity.called",
        time=datetime.now(UTC),
        data=ActivityEventData(
            actor=ActivityActor(id="user", type="user"),
            company_id=company,
        ),
    )
    return event.to_wire()


def row(company: str = "c1", event_id: str | None = None) -> Row:
    event_payload = payload(company, event_id)
    return Row(
        id=event_payload["id"],
        company_id=company,
        payload=event_payload,
    )


def relay(
    store: Store,
    publisher: Publisher | None = None,
    flags: Flags | None = None,
    metrics: Metrics | None = None,
    **kwargs: Any,
) -> tuple[OutboxRelay, Metrics, Publisher, Flags]:
    metric = metrics or Metrics()
    broker = publisher or Publisher()
    flag_client = flags or Flags({"c1": FlagEvaluation(value=True, reason="remote")})
    return (
        OutboxRelay(
            store,
            broker,
            flag_client,
            metric,
            **kwargs,
        ),
        metric,
        broker,
        flag_client,
    )


async def wait_until(condition: Any, timeout: float = 2.0) -> None:
    """Poll ``condition`` so a regression fails with a timeout instead of hanging."""

    async def poll() -> None:
        while not condition():
            await asyncio.sleep(0.001)

    await asyncio.wait_for(poll(), timeout)


async def test_flag_on_deletes_after_confirm_and_counts_sent() -> None:
    store = Store([row()])
    relay_instance, metrics, publisher, flags = relay(store)

    assert await relay_instance.run_once() == 1
    assert not store.rows
    assert len(publisher.calls) == 1
    assert (
        metrics.value(
            "unique_activity_events_total",
            {
                "outcome": "sent",
                "source": "svc",
                "actorType": "user",
                "eventType": "activity.called",
            },
        )
        == 1
    )
    assert len(flags.calls) == 1


async def test_sent_counts_only_rows_removed_by_fenced_delete() -> None:
    first, second = row(), row(event_id=str(uuid4()))
    store = Store([first, second])
    store.drop_deleted_ids.add(second.id)
    relay_instance, metrics, publisher, _ = relay(store)

    assert await relay_instance.run_once() == 1
    assert len(publisher.calls) == 1
    assert (
        metrics.value(
            "unique_activity_events_total",
            {
                "outcome": "sent",
                "source": "svc",
                "actorType": "user",
                "eventType": "activity.called",
            },
        )
        == 1
    )


async def test_flag_off_discards_without_publishing() -> None:
    store = Store([row()])
    relay_instance, metrics, publisher, _ = relay(
        store,
        flags=Flags({"c1": FlagEvaluation(value=False, reason="remote")}),
    )

    assert await relay_instance.run_once() == 1
    assert not store.rows
    assert publisher.calls == []
    assert metrics.value("unique_activity_event_outbox_discarded_total") == 1


@pytest.mark.parametrize(
    "evaluation",
    [
        FlagEvaluation(value=False, reason="fallback"),
        FlagEvaluation(value=False, reason="stale"),
        RuntimeError("flag payload"),
    ],
)
async def test_unknown_flag_defers_and_is_remembered(
    evaluation: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = [0.0]
    monkeypatch.setattr(relay_module, "time", SimpleNamespace(monotonic=lambda: now[0]))
    store = Store([row()])
    relay_instance, metrics, _, flags = relay(store, flags=Flags({"c1": evaluation}))

    assert await relay_instance.run_once() == 0
    assert await relay_instance.run_once() == 0

    assert len(flags.calls) == 1
    assert metrics.value("unique_activity_event_outbox_flag_check_failures_total") == 1
    assert store.rows
    assert [delay for _, delay in store.defer_calls if delay] == [
        OUTBOX_RELAY_TIMINGS.flag_unknown_defer_seconds
    ] * 2

    now[0] = 16
    flags.values["c1"] = FlagEvaluation(value=True, reason="remote")
    assert await relay_instance.run_once() == 1
    assert not store.rows


async def test_stale_true_flag_is_on() -> None:
    store = Store([row()])
    relay_instance, metrics, _, _ = relay(
        store, flags=Flags({"c1": FlagEvaluation(value=True, reason="stale")})
    )

    assert await relay_instance.run_once() == 1
    assert not store.rows
    assert metrics.value("unique_activity_event_outbox_flag_check_failures_total") == 0


async def test_cached_off_defers_quietly_and_deletes_nothing() -> None:
    store = Store([row()])
    relay_instance, metrics, publisher, flags = relay(
        store,
        flags=Flags({"c1": FlagEvaluation(value=False, reason="cached")}),
    )

    assert await relay_instance.run_once() == 0
    assert store.rows
    assert store.delete_calls == []
    assert publisher.calls == []
    assert store.defer_calls[0] == (
        [store.rows[0].id],
        OUTBOX_RELAY_TIMINGS.flag_unknown_defer_seconds,
    )
    assert len(flags.calls) == 1
    assert metrics.value("unique_activity_event_outbox_flag_check_failures_total") == 0
    assert metrics.value("unique_activity_event_outbox_discarded_total") == 0


async def test_cached_off_is_not_remembered_and_a_remote_off_then_deletes() -> None:
    evaluations = iter(
        [
            FlagEvaluation(value=False, reason="cached"),
            FlagEvaluation(value=False, reason="remote"),
        ]
    )
    store = Store([row()])
    relay_instance, metrics, _, flags = relay(
        store, flags=Flags({"c1": lambda: next(evaluations)})
    )

    assert await relay_instance.run_once() == 0
    assert await relay_instance.run_once() == 1
    assert not store.rows
    assert len(flags.calls) == 2
    assert metrics.value("unique_activity_event_outbox_discarded_total") == 1


async def test_cached_on_is_delivered() -> None:
    store = Store([row()])
    relay_instance, _, publisher, _ = relay(
        store,
        flags=Flags({"c1": FlagEvaluation(value=True, reason="cached")}),
    )

    assert await relay_instance.run_once() == 1
    assert not store.rows
    assert len(publisher.calls) == 1


async def test_companies_are_grouped_without_mixing_messages() -> None:
    rows = [row("c1"), row("c2"), row("c1")]
    flags = Flags(
        {
            "c1": FlagEvaluation(value=True, reason="remote"),
            "c2": FlagEvaluation(value=True, reason="remote"),
        }
    )
    store = Store(rows)
    relay_instance, _, publisher, _ = relay(store, flags=flags)

    assert await relay_instance.run_once() == 3
    assert len(publisher.calls) == 2
    assert [
        {event["data"]["companyId"] for event in batch} for batch in publisher.calls
    ] == [
        {"c1"},
        {"c2"},
    ]


def _schema_invalid_rows() -> list[Row]:
    over_cap = row("c1")
    over_cap.payload["data"]["targetName"] = "x" * 257
    snake_case = row("c1")
    data = snake_case.payload["data"]
    data["company_id"] = data.pop("companyId")
    return [Row("invalid", "c1", {"id": "invalid"}), over_cap, snake_case]


@pytest.mark.parametrize(
    "invalid", _schema_invalid_rows(), ids=["missing", "over-cap", "snake-case-keys"]
)
async def test_invalid_event_is_published_alone_and_counted(invalid: Row) -> None:
    store = Store([invalid, row("c1")])
    relay_instance, metrics, publisher, _ = relay(store)

    assert await relay_instance.run_once() == 2
    assert [len(events) for events in publisher.calls] == [1, 1]
    assert publisher.calls[0][0] == invalid.payload
    assert metrics.value("unique_activity_event_outbox_invalid_events_total") == 1


async def test_timeout_backs_off_current_message_and_defers_untried_messages() -> None:
    first, second = row(event_id=str(uuid4())), row(event_id=str(uuid4()))
    store = Store([first, second])
    relay_instance, metrics, publisher, _ = relay(
        store,
        publisher=Publisher(["timeout"]),
        max_batch_size_bytes=1,
        max_data_size_bytes=100_000,
    )

    assert await relay_instance.run_once() == 1
    assert publisher.calls == [[first.payload]]
    assert store.backoff_calls == [[first.id]]
    assert (
        [second.id],
        OUTBOX_RELAY_TIMINGS.untried_defer_seconds,
    ) in store.defer_calls
    assert first.attempts == 1 and second.attempts == 0
    assert (
        metrics.value(
            "unique_activity_event_outbox_publish_failures_total",
            {"reason": "timeout"},
        )
        == 1
    )


async def test_rejected_multi_row_message_retries_rows_alone(
    caplog: pytest.LogCaptureFixture,
) -> None:
    rows = [row(event_id=str(uuid4())) for _ in range(3)]
    middle_id = rows[1].id
    store = Store(rows)
    relay_instance, metrics, publisher, _ = relay(
        store, publisher=Publisher(["reject", "ok", "reject", "ok"])
    )

    assert await relay_instance.run_once() == 3
    assert [len(events) for events in publisher.calls] == [3, 1, 1, 1]
    assert store.backoff_calls == [[middle_id]]
    assert {r.id for r in store.rows} == {middle_id}
    assert store.last_errors == ["RuntimeError"]
    assert (
        metrics.value(
            "unique_activity_event_outbox_publish_failures_total",
            {"reason": "rejected"},
        )
        == 2
    )
    assert all("secret payload" not in record.getMessage() for record in caplog.records)


async def test_backoff_max_counter_is_once_when_attempt_reaches_cap() -> None:
    item = row()
    item.attempts = 10
    store = Store([item])
    relay_instance, metrics, publisher, _ = relay(
        store, publisher=Publisher(["reject", "reject"])
    )

    assert await relay_instance.run_once() == 1
    assert await relay_instance.run_once() == 1
    assert metrics.value("unique_activity_event_outbox_backoff_max_reached_total") == 1


async def test_deadline_stops_before_publishing_the_next_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock_value = [0.0]
    monkeypatch.setattr(
        relay_module, "time", SimpleNamespace(monotonic=lambda: clock_value[0])
    )
    rows = [row(event_id=str(uuid4())) for _ in range(2)]
    second_id = rows[1].id
    store = Store(rows)
    publisher = Publisher()

    async def publish(events: list[dict[str, Any]]) -> None:
        publisher.calls.append(events)
        clock_value[0] = 46.0

    relay_instance, _, _, _ = relay(
        store,
        publisher=publisher,
        max_batch_size_bytes=1,
        max_data_size_bytes=100_000,
    )
    publisher.publish = publish

    assert await relay_instance.run_once() == 1
    assert len(publisher.calls) == 1
    assert second_id in {item for ids, _ in store.defer_calls for item in ids}


async def test_relay_loop_survives_claim_error_and_refreshes_gauges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        relay_module,
        "OUTBOX_RELAY_TIMINGS",
        replace(
            OUTBOX_RELAY_TIMINGS,
            idle_poll_seconds=0.001,
            stats_interval_seconds=0,
        ),
    )
    store = Store([row()])
    store.claim_errors.append(ConnectionResetError("secret payload"))
    store.stats_value = (4, 12.5, 2)
    relay_instance, metrics, _, _ = relay(store)
    await relay_instance.start()
    try:
        for _ in range(100):
            if not store.rows:
                break
            await asyncio.sleep(0.001)
        assert not store.rows
        assert store.claim_calls >= 2
        assert metrics.value("unique_activity_event_outbox_pending_rows") == 4
    finally:
        await relay_instance.stop()


async def test_full_settled_batch_is_polled_without_idle_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        relay_module,
        "OUTBOX_RELAY_TIMINGS",
        replace(OUTBOX_RELAY_TIMINGS, idle_poll_seconds=1),
    )
    store = Store([row(event_id=str(uuid4())) for _ in range(100)])
    relay_instance, _, _, _ = relay(store)
    await relay_instance.start()
    try:
        await wait_until(lambda: store.claim_calls >= 2)
    finally:
        await relay_instance.stop()


async def test_deferred_full_batch_waits_for_idle_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        relay_module,
        "OUTBOX_RELAY_TIMINGS",
        replace(OUTBOX_RELAY_TIMINGS, idle_poll_seconds=0.3),
    )
    store = Store([row(event_id=str(uuid4())) for _ in range(100)])
    relay_instance, _, _, _ = relay(
        store,
        flags=Flags({"c1": FlagEvaluation(value=False, reason="fallback")}),
    )
    await relay_instance.start()
    try:
        await wait_until(lambda: store.claim_calls >= 1)
        assert store.claim_calls == 1
        await asyncio.sleep(0.05)
        assert store.claim_calls == 1
        await wait_until(lambda: store.claim_calls >= 2)
    finally:
        await relay_instance.stop()


async def test_flag_timeout_defers_and_reads_companies_in_parallel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        relay_module,
        "OUTBOX_RELAY_TIMINGS",
        replace(OUTBOX_RELAY_TIMINGS, flag_check_timeout_seconds=0.001),
    )
    started: set[str] = set()
    gate = asyncio.Event()

    class HangingFlags:
        async def evaluate(self, _flag: str, *, company_id: str) -> FlagEvaluation:
            started.add(company_id)
            await gate.wait()
            return FlagEvaluation(value=True, reason="remote")

    companies = ["c1", "c2", "c3"]
    store = Store([row(company) for company in companies])
    relay_instance, metrics, _, _ = relay(store, flags=HangingFlags())

    assert await relay_instance.run_once() == 0
    assert started == set(companies)
    assert metrics.value("unique_activity_event_outbox_flag_check_failures_total") == 3
    assert all(
        delay == OUTBOX_RELAY_TIMINGS.flag_unknown_defer_seconds
        for _, delay in store.defer_calls
        if delay
    )


async def test_schema_check_error_keeps_relay_unready() -> None:
    class BrokenSchemaStore(Store):
        checks = 0

        async def has_expected_columns(self) -> bool:
            self.checks += 1
            raise ConnectionError("secret payload")

    store = BrokenSchemaStore([])
    relay_instance, _, _, _ = relay(store)
    await relay_instance.start()
    await wait_until(lambda: store.checks >= 1)
    assert not relay_instance.is_ready()
    await relay_instance.stop()


async def test_schema_mismatch_retries_and_then_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        relay_module,
        "OUTBOX_RELAY_TIMINGS",
        replace(OUTBOX_RELAY_TIMINGS, schema_recheck_seconds=0.001),
    )
    checks = 0

    class CountingStore(Store):
        async def has_expected_columns(self) -> bool:
            nonlocal checks
            checks += 1
            return await super().has_expected_columns()

    store = CountingStore([], schema_ok=False)
    relay_instance, _, _, _ = relay(store)
    await relay_instance.start()
    await wait_until(lambda: checks >= 4)
    assert not relay_instance.is_ready()
    store.schema_ok = True
    await wait_until(relay_instance.is_ready)
    await relay_instance.stop()


async def test_stop_cancels_stuck_publish_after_timeout_and_hands_claim_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()
    store = Store([row()])

    class BlockingPublisher(Publisher):
        async def publish(self, events: list[dict[str, Any]]) -> None:
            self.calls.append(events)
            started.set()
            await asyncio.Event().wait()

    monkeypatch.setattr(
        relay_module,
        "OUTBOX_RELAY_TIMINGS",
        replace(OUTBOX_RELAY_TIMINGS, stop_timeout_seconds=0.01),
    )
    relay_instance, _, _, _ = relay(store, publisher=BlockingPublisher())
    await relay_instance.start()
    await asyncio.wait_for(started.wait(), 1)
    await relay_instance.stop()

    assert store.claimed == set()
    assert store.defer_calls[-1][1] == 0


async def test_stop_waits_for_current_round_before_handing_claim_back() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    store = Store([row()])

    class BlockingPublisher(Publisher):
        async def publish(self, events: list[dict[str, Any]]) -> None:
            self.calls.append(events)
            started.set()
            await release.wait()

    relay_instance, _, publisher, _ = relay(
        store,
        publisher=BlockingPublisher(),
    )
    await relay_instance.start()
    await asyncio.wait_for(started.wait(), 1)

    stopping = asyncio.create_task(relay_instance.stop())
    await asyncio.sleep(0.1)
    assert not stopping.done()

    release.set()
    await stopping

    assert store.rows == []
    assert len(publisher.calls) == 1
    assert store.claimed == set()


async def test_stop_propagates_caller_cancellation_and_finishes_relay() -> None:
    started = asyncio.Event()
    store = Store([row()])

    class BlockingPublisher(Publisher):
        async def publish(self, events: list[dict[str, Any]]) -> None:
            self.calls.append(events)
            started.set()
            await asyncio.Event().wait()

    relay_instance, _, _, _ = relay(store, publisher=BlockingPublisher())
    await relay_instance.start()
    await asyncio.wait_for(started.wait(), 1)

    stopping = asyncio.create_task(relay_instance.stop())
    await asyncio.sleep(0.05)
    stopping.cancel()
    with pytest.raises(asyncio.CancelledError):
        await stopping

    assert store.claimed == set()


class _BlockedThenFailingPublisher(Publisher):
    """Blocks until ``fail`` is set, then rejects like a connection cut by shutdown."""

    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.fail = asyncio.Event()

    async def publish(self, events: list[dict[str, Any]]) -> None:
        self.calls.append(events)
        self.started.set()
        await self.fail.wait()
        raise RuntimeError("Channel closed")


@pytest.mark.parametrize("row_count", [1, 2])
async def test_a_publish_that_fails_after_stop_is_neither_counted_nor_backed_off(
    row_count: int, caplog: pytest.LogCaptureFixture
) -> None:
    store = Store([row() for _ in range(row_count)])
    publisher = _BlockedThenFailingPublisher()
    relay_instance, metrics, _, _ = relay(store, publisher=publisher)
    await relay_instance.start()
    await asyncio.wait_for(publisher.started.wait(), 1)

    stopping = asyncio.create_task(relay_instance.stop())
    await asyncio.sleep(0.05)
    publisher.fail.set()
    await stopping

    assert len(publisher.calls) == 1
    assert (
        metrics.value(
            "unique_activity_event_outbox_publish_failures_total",
            {"reason": "rejected"},
        )
        == 0
    )
    assert store.backoff_calls == []
    assert store.claimed == set()
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


async def test_a_sender_that_never_returns_is_a_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HangingPublisher(Publisher):
        async def publish(self, events: list[dict[str, Any]]) -> None:
            self.calls.append(events)
            await asyncio.Event().wait()

    monkeypatch.setattr(
        relay_module,
        "OUTBOX_RELAY_TIMINGS",
        replace(OUTBOX_RELAY_TIMINGS, publish_timeout_seconds=0.01),
    )
    store = Store([row("c1"), row("c2")])
    flags = Flags(
        {
            "c1": FlagEvaluation(value=True, reason="remote"),
            "c2": FlagEvaluation(value=True, reason="remote"),
        }
    )
    relay_instance, metrics, publisher, _ = relay(
        store, publisher=HangingPublisher(), flags=flags
    )

    await asyncio.wait_for(relay_instance.run_once(), 1)

    assert len(publisher.calls) == 1
    assert (
        metrics.value(
            "unique_activity_event_outbox_publish_failures_total",
            {"reason": "timeout"},
        )
        == 1
    )
    assert len(store.backoff_calls) == 1
    assert store.defer_calls[0][1] == OUTBOX_RELAY_TIMINGS.untried_defer_seconds


async def test_a_connection_error_in_the_schema_check_is_not_a_missing_table(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        relay_module,
        "OUTBOX_RELAY_TIMINGS",
        replace(OUTBOX_RELAY_TIMINGS, schema_recheck_seconds=0.001),
    )
    checks = 0

    class FlakyStore(Store):
        async def has_expected_columns(self) -> bool:
            nonlocal checks
            checks += 1
            if checks <= 3:
                raise ConnectionError("secret payload")
            return await super().has_expected_columns()

    store = FlakyStore([], schema_ok=False)
    relay_instance, _, _, _ = relay(store)
    await relay_instance.start()
    await wait_until(lambda: checks >= 6)
    await relay_instance.stop()

    unreachable = [r for r in caplog.records if "ConnectionError" in r.getMessage()]
    mismatches = [r for r in caplog.records if "table is missing" in r.getMessage()]
    assert len(unreachable) == 1
    assert len(mismatches) == 1
    assert "secret payload" not in caplog.text


async def test_a_non_object_payload_does_not_end_the_round() -> None:
    bad = Row(id=str(uuid4()), company_id="c1", payload="not an object")  # type: ignore[arg-type]
    store = Store([bad, row()])
    relay_instance, metrics, _, _ = relay(store)

    assert await relay_instance.run_once() == 2

    assert store.rows == []
    assert (
        metrics.value(
            "unique_activity_events_total",
            {
                "outcome": "sent",
                "source": "svc",
                "actorType": "user",
                "eventType": "activity.called",
            },
        )
        == 1
    )


class _DeleteFailsStore(Store):
    async def delete_claimed(self, _token: str, ids: list[str]) -> list[str]:
        raise ConnectionError("secret payload")


async def test_a_failed_delete_after_a_publish_is_visible_in_the_loop_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    relay_instance, _, publisher, _ = relay(_DeleteFailsStore([row()]))
    await relay_instance.start()
    try:
        await wait_until(
            lambda: any(
                "iteration failed" in r.getMessage()
                and "ConnectionError" in r.getMessage()
                for r in caplog.records
            )
        )
    finally:
        await relay_instance.stop()

    assert len(publisher.calls) >= 1
    assert "secret payload" not in caplog.text


async def test_a_failing_delete_in_the_flag_off_path_releases_the_claim() -> None:
    store = _DeleteFailsStore([row()])
    relay_instance, _, publisher, _ = relay(
        store, flags=Flags({"c1": FlagEvaluation(value=False, reason="remote")})
    )

    with pytest.raises(ConnectionError):
        await relay_instance.run_once()

    assert publisher.calls == []
    assert store.claimed == set()
    assert store.defer_calls[-1][1] == 0


async def test_a_stopped_relay_can_be_started_again() -> None:
    store = Store([])
    relay_instance, _, publisher, _ = relay(store)
    await relay_instance.start()
    await wait_until(relay_instance.is_ready)
    await relay_instance.stop()
    assert not relay_instance.is_ready()

    store.rows.append(row())
    await relay_instance.start()
    try:
        await wait_until(lambda: store.rows == [])
    finally:
        await relay_instance.stop()

    assert len(publisher.calls) == 1


async def test_stop_propagates_the_callers_cancellation_while_a_release_is_stuck(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()
    release_gate = asyncio.Event()

    class StuckReleaseStore(Store):
        async def defer(self, token: str, ids: list[str], delay: int) -> int:
            await release_gate.wait()
            return await super().defer(token, ids, delay)

    class BlockingPublisher(Publisher):
        async def publish(self, events: list[dict[str, Any]]) -> None:
            self.calls.append(events)
            started.set()
            await asyncio.Event().wait()

    monkeypatch.setattr(
        relay_module,
        "OUTBOX_RELAY_TIMINGS",
        replace(OUTBOX_RELAY_TIMINGS, stop_timeout_seconds=0.01),
    )
    relay_instance, _, _, _ = relay(
        StuckReleaseStore([row()]), publisher=BlockingPublisher()
    )
    await relay_instance.start()
    await asyncio.wait_for(started.wait(), 1)
    stopping = asyncio.create_task(relay_instance.stop())
    await asyncio.sleep(0.1)
    assert not stopping.done()

    stopping.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(stopping, 1)

    release_gate.set()
    await asyncio.sleep(0.05)


async def test_gauges_refresh_while_a_round_is_stuck_in_a_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    class BlockingPublisher(Publisher):
        async def publish(self, events: list[dict[str, Any]]) -> None:
            self.calls.append(events)
            started.set()
            await release.wait()

    monkeypatch.setattr(
        relay_module,
        "OUTBOX_RELAY_TIMINGS",
        replace(OUTBOX_RELAY_TIMINGS, stats_interval_seconds=0.01),
    )
    store = Store([row()])
    store.stats_value = (4, 12.5, 2)
    relay_instance, metrics, _, _ = relay(store, publisher=BlockingPublisher())
    await relay_instance.start()
    await asyncio.wait_for(started.wait(), 1)

    await wait_until(
        lambda: metrics.value("unique_activity_event_outbox_pending_rows") == 4
    )
    release.set()
    await relay_instance.stop()
    assert not [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
