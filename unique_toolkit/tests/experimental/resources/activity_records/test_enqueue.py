from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import import_module
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext

pytest.importorskip("asyncpg", reason="Enqueue tests start the outbox with its store")

from unique_toolkit.experimental.resources.activity_records import (
    prepare as prepare_module,
)
from unique_toolkit.experimental.resources.activity_records.enqueue import (
    ActivityRecordsOutbox,
    drain,
    enqueue,
)
from unique_toolkit.experimental.resources.activity_records.schemas import (
    ActivityActor,
    ActivityCloudEvent,
    ActivityEventData,
)
from unique_toolkit.experimental.resources.feature_flags.schemas import FlagEvaluation

from .conftest import Metrics

pytestmark = pytest.mark.ai

enqueue_module = import_module(
    "unique_toolkit.experimental.resources.activity_records.enqueue"
)
store_module = import_module(
    "unique_toolkit.experimental.resources.activity_records.store"
)


class Store:
    def __init__(
        self,
        gate: asyncio.Event | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.gate = gate
        self.error = error
        self.rows: list[Any] = []

    async def insert(self, rows: list[Any]) -> None:
        if self.gate is not None:
            await self.gate.wait()
        if self.error is not None:
            raise self.error
        self.rows.extend(rows)


class FlagClient:
    def __init__(
        self,
        evaluation: FlagEvaluation | None = None,
        *,
        error: BaseException | None = None,
        gate: asyncio.Event | None = None,
    ) -> None:
        self.evaluation = evaluation
        self.error = error
        self.gate = gate
        self.calls = 0
        self.company_ids: list[str] = []

    async def evaluate(self, _flag: str, *, company_id: str) -> FlagEvaluation:
        assert company_id
        self.calls += 1
        self.company_ids.append(company_id)
        if self.gate is not None:
            await self.gate.wait()
        if self.error is not None:
            raise self.error
        assert self.evaluation is not None
        return self.evaluation


def event(critical_data: dict[str, Any] | None = None) -> ActivityCloudEvent:
    return ActivityCloudEvent(
        source="web-search",
        type="web-search.tool.called",
        time=datetime.now(UTC),
        data=ActivityEventData(
            actor=ActivityActor(id="user", type="user"),
            company_id="company-1",
            critical_data=critical_data,
        ),
    )


class Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


def event_for(company_id: str) -> ActivityCloudEvent:
    built = event()
    built.data.company_id = company_id
    return built


class Pool:
    def __init__(self, wiring: Wiring, *, close_hangs: bool = False) -> None:
        self.wiring = wiring
        self.close_hangs = close_hangs

    async def close(self) -> None:
        if self.close_hangs:
            await asyncio.Event().wait()
        self.wiring.pools_closed += 1
        self.wiring.calls.append("pool.close")

    def terminate(self) -> None:
        self.wiring.pools_terminated += 1


class StubRelay:
    def __init__(self, error: BaseException | None, calls: list[str]) -> None:
        self.error = error
        self.calls = calls

    async def start(self) -> None:
        self.calls.append("relay.start")
        if self.error is not None:
            raise self.error

    async def stop(self) -> None:
        self.calls.append("relay.stop")

    def is_ready(self) -> bool:
        return True


@dataclass
class Wiring:
    relays: list[StubRelay] = field(default_factory=list)
    relay_flag_clients: list[Any] = field(default_factory=list)
    pools_closed: int = 0
    pools_terminated: int = 0
    calls: list[str] = field(default_factory=list)


_started: list[ActivityRecordsOutbox] = []


@pytest.fixture(autouse=True)
async def stop_started_outboxes(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[None]:
    monkeypatch.setattr(enqueue_module, "_last_metrics", None)
    yield
    for outbox in _started:
        await outbox.stop()
    _started.clear()


def patch_runtime(
    monkeypatch: pytest.MonkeyPatch,
    store: Any,
    *,
    pool_gate: asyncio.Event | None = None,
    relay_error: BaseException | None = None,
    pool_close_hangs: bool = False,
) -> Wiring:
    """Patch the database and relay so `ActivityRecordsOutbox.start()` runs offline."""
    wiring = Wiring()

    async def create_pool(_url: str, **_options: Any) -> Pool:
        if pool_gate is not None:
            await pool_gate.wait()
        return Pool(wiring, close_hangs=pool_close_hangs)

    def create_relay(*args: Any, **_kwargs: Any) -> StubRelay:
        wiring.relay_flag_clients.append(args[2])
        wiring.relays.append(StubRelay(relay_error, wiring.calls))
        return wiring.relays[-1]

    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    monkeypatch.setattr(store_module, "create_pool", create_pool)
    monkeypatch.setattr(store_module, "OutboxStore", lambda _pool: store)
    monkeypatch.setattr(enqueue_module, "OutboxRelay", create_relay)
    return wiring


def new_outbox(
    metrics: Metrics, flag_client: FlagClient | None = None
) -> ActivityRecordsOutbox:
    outbox = ActivityRecordsOutbox(
        publisher=AsyncMock(),
        flag_client=flag_client
        or FlagClient(FlagEvaluation(value=True, reason="remote")),
        metrics=metrics.metrics,
    )
    _started.append(outbox)
    return outbox


async def activate(
    monkeypatch: pytest.MonkeyPatch,
    store: Store,
    metrics: Metrics,
    flag_client: FlagClient | None = None,
    *,
    max_data_size_bytes: int | None = None,
    clock: Callable[[], float] | None = None,
) -> ActivityRecordsOutbox:
    patch_runtime(monkeypatch, store)
    if max_data_size_bytes is not None:
        monkeypatch.setenv(
            "ACTIVITY_RECORDS_MAX_DATA_SIZE_BYTES", str(max_data_size_bytes)
        )
    if clock is not None:
        monkeypatch.setattr(enqueue_module, "time", SimpleNamespace(monotonic=clock))
    outbox = new_outbox(metrics, flag_client)
    await outbox.start()
    return outbox


async def activate_with_pending_pool(
    monkeypatch: pytest.MonkeyPatch,
    store: Store,
    metrics: Metrics,
    pool_gate: asyncio.Event,
) -> asyncio.Task[None]:
    """Start the outbox and leave `start()` waiting for the pool."""
    patch_runtime(monkeypatch, store, pool_gate=pool_gate)
    starting = asyncio.create_task(new_outbox(metrics).start())
    await asyncio.sleep(0)
    return starting


async def test_enqueue_returns_synchronously_and_inserts_in_the_background(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = asyncio.Event()
    store = Store(gate)
    await activate(monkeypatch, store, Metrics())

    assert enqueue(event()) is None
    await asyncio.sleep(0)
    assert store.rows == []

    gate.set()
    await drain()
    assert len(store.rows) == 1


async def test_insert_waits_for_the_pool_then_inserts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store()
    pool_gate = asyncio.Event()
    starting = await activate_with_pending_pool(
        monkeypatch, store, Metrics(), pool_gate
    )

    enqueue(event())
    await asyncio.sleep(0)
    assert store.rows == []

    pool_gate.set()
    await starting
    await drain()
    assert len(store.rows) == 1


async def test_pool_wait_timeout_counts_failure_and_drops(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(enqueue_module, "POOL_WAIT_TIMEOUT_SECONDS", 0.001)
    metrics = Metrics()
    starting = await activate_with_pending_pool(
        monkeypatch, Store(), metrics, asyncio.Event()
    )

    enqueue(event())
    await drain()

    assert metrics.value("unique_activity_event_outbox_record_failures_total") == 1
    assert "errorName=TimeoutError" in caplog.text
    starting.cancel()
    await asyncio.gather(starting, return_exceptions=True)


@pytest.mark.parametrize("reason", ["remote", "cached"])
async def test_fresh_or_cached_off_skips_insert(
    reason: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store()
    metrics = Metrics()
    flags = FlagClient(FlagEvaluation(value=False, reason=reason))
    await activate(monkeypatch, store, metrics, flags)

    assert enqueue(event()) is None
    await drain()

    assert flags.calls == 1
    assert store.rows == []
    assert metrics.value("unique_activity_event_outbox_record_failures_total") == 0


async def test_cached_off_skips_truncation_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store()
    metrics = Metrics()
    await activate(
        monkeypatch,
        store,
        metrics,
        FlagClient(FlagEvaluation(value=False, reason="cached")),
        max_data_size_bytes=2_000,
    )

    enqueue(event({"blob": "x" * 10_000}))
    await drain()

    assert store.rows == []
    assert metrics.value("unique_activity_events_total") == 0


@pytest.mark.parametrize("reason", ["stale", "fallback", "remote"])
async def test_unknown_or_on_flag_inserts(
    reason: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store()
    metrics = Metrics()
    flags = FlagClient(FlagEvaluation(value=reason == "remote", reason=reason))
    await activate(monkeypatch, store, metrics, flags)

    enqueue(event())
    await drain()

    assert flags.calls == 1
    assert len(store.rows) == 1
    assert metrics.value("unique_activity_event_outbox_record_failures_total") == 0


@pytest.mark.parametrize("failure", ["error", "timeout"])
async def test_failed_flag_read_starts_cooldown_and_inserts_directly(
    failure: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(enqueue_module, "_FIRST_FLAG_READ_TIMEOUT_SECONDS", 0.001)
    store = Store()
    metrics = Metrics()
    clock = Clock()
    flags = (
        FlagClient(error=RuntimeError("secret payload"))
        if failure == "error"
        else FlagClient(gate=asyncio.Event())
    )
    await activate(monkeypatch, store, metrics, flags, clock=clock)

    enqueue(event())
    await drain()
    clock.now += 14
    enqueue(event())
    await drain()

    error_name = "RuntimeError" if failure == "error" else "TimeoutError"
    assert flags.calls == 1
    assert len(store.rows) == 2
    assert metrics.value("unique_activity_event_outbox_record_failures_total") == 0
    assert "Could not refresh the activity records flag" in caplog.text
    assert f"companyId=company-1 errorName={error_name}" in caplog.text
    assert "secret payload" not in caplog.text


async def test_flag_is_read_again_after_the_cooldown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = Clock()
    flags = FlagClient(error=RuntimeError("down"))
    await activate(monkeypatch, Store(), Metrics(), flags, clock=clock)

    enqueue(event())
    await drain()
    clock.now += 15
    enqueue(event())
    await drain()

    assert flags.calls == 2


async def test_cooldown_is_per_company(monkeypatch: pytest.MonkeyPatch) -> None:
    flags = FlagClient(error=RuntimeError("down"))
    await activate(monkeypatch, Store(), Metrics(), flags, clock=Clock())

    enqueue(event_for("company-1"))
    await drain()
    enqueue(event_for("company-2"))
    await drain()
    enqueue(event_for("company-1"))
    await drain()

    assert flags.company_ids == ["company-1", "company-2"]


async def test_drain_waits_for_the_write_path_flag_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = asyncio.Event()
    store = Store()
    flags = FlagClient(FlagEvaluation(value=True, reason="remote"), gate=gate)
    await activate(monkeypatch, store, Metrics(), flags)

    enqueue(event())
    await asyncio.sleep(0)
    assert flags.calls == 1
    assert store.rows == []

    gate.set()
    await drain()
    assert len(store.rows) == 1


async def test_correlation_id_is_taken_before_background_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store()
    await activate(monkeypatch, store, Metrics())
    context = SpanContext(trace_id=0xABC, span_id=1, is_remote=False)

    with trace.use_span(NonRecordingSpan(context)):
        enqueue(event())

    await drain()
    assert store.rows[0].payload["data"]["correlationId"] == format(0xABC, "032x")


async def test_truncation_is_counted_at_record_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store()
    metrics = Metrics()
    await activate(monkeypatch, store, metrics, max_data_size_bytes=2_000)

    enqueue(event({"blob": "x" * 10_000}))

    event_labels = {
        "outcome": "truncated",
        "source": "web-search",
        "actorType": "user",
        "eventType": "web-search.tool.called",
    }
    assert metrics.value("unique_activity_events_total", event_labels) == 0
    await drain()
    assert metrics.value("unique_activity_events_total", event_labels) == 1
    assert store.rows[0].payload["data"]["criticalData"]["truncated"] is True


async def test_built_event_with_cut_metadata_is_counted_truncated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store()
    metrics = Metrics()
    await activate(monkeypatch, store, metrics)
    built = ActivityCloudEvent.build(
        source="web-search",
        type="web-search.tool.called",
        data={"actor": {"id": "u" * 200, "type": "user"}, "companyId": "company-1"},
    )

    enqueue(built)
    await drain()

    assert store.rows[0].payload["data"]["actor"]["id"] == "u" * 128
    assert (
        metrics.value(
            "unique_activity_events_total",
            {
                "outcome": "truncated",
                "source": "web-search",
                "actorType": "user",
                "eventType": "web-search.tool.called",
            },
        )
        == 1
    )


async def test_nul_is_replaced_before_insert(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store()
    await activate(monkeypatch, store, Metrics())

    enqueue(event({"key\x00": "value\x00"}))
    await drain()

    assert store.rows[0].payload["data"]["criticalData"] == {"key�": "value�"}


async def test_an_unsafe_company_id_is_rejected_and_counted_as_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store()
    metrics = Metrics()
    await activate(monkeypatch, store, metrics)

    enqueue(event_for("co\x00mpany"))
    await drain()

    assert store.rows == []
    assert metrics.value("unique_activity_event_outbox_record_failures_total") == 1


async def test_failing_store_never_raises_and_counts_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    metrics = Metrics()
    await activate(monkeypatch, Store(error=RuntimeError("secret payload")), metrics)

    enqueue(event())
    await drain()

    assert metrics.value("unique_activity_event_outbox_record_failures_total") == 1
    assert all("secret payload" not in record.getMessage() for record in caplog.records)


def test_no_running_loop_never_raises_and_counts_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics = Metrics()
    asyncio.run(activate(monkeypatch, Store(), metrics))

    enqueue(event())

    assert metrics.value("unique_activity_event_outbox_record_failures_total") == 1
    asyncio.run(_started[0].stop())


async def test_unconfigured_never_raises(caplog: pytest.LogCaptureFixture) -> None:
    assert enqueue(event()) is None
    assert "no Activity Records outbox is running" in caplog.text
    assert "errorName=RuntimeError" not in caplog.text


async def test_drain_times_out_without_cancelling_insert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = asyncio.Event()
    store = Store(gate)
    await activate(monkeypatch, store, Metrics())

    enqueue(event())
    await drain(timeout=0.001)
    assert store.rows == []

    gate.set()
    await drain()
    assert len(store.rows) == 1


async def test_enqueue_during_stop_is_counted_and_not_inserted(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    gate = asyncio.Event()
    store = Store(gate)
    metrics = Metrics()
    outbox = await activate(monkeypatch, store, metrics)

    enqueue(event())
    stopping = asyncio.create_task(outbox.stop())
    await asyncio.sleep(0)
    enqueue(event_for("late-company"))
    gate.set()
    await stopping

    assert len(store.rows) == 1
    assert metrics.value("unique_activity_event_outbox_record_failures_total") == 1
    assert "no Activity Records outbox is running" in caplog.text
    assert "companyId=late-company" in caplog.text


async def test_a_second_active_outbox_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await activate(monkeypatch, Store(), Metrics())

    with pytest.raises(RuntimeError, match="Only one Activity Records outbox"):
        await new_outbox(Metrics()).start()


async def test_start_twice_on_one_outbox_is_a_no_op(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wiring = patch_runtime(monkeypatch, Store())
    outbox = new_outbox(Metrics())

    await outbox.start()
    await outbox.start()

    assert len(wiring.relays) == 1


async def test_stop_without_start_is_a_no_op() -> None:
    await ActivityRecordsOutbox(publisher=AsyncMock()).stop()


async def test_stop_after_a_failed_start_is_a_no_op(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_runtime(monkeypatch, Store(), relay_error=RuntimeError("relay failed"))
    outbox = new_outbox(Metrics())
    with pytest.raises(RuntimeError, match="relay failed"):
        await outbox.start()

    await outbox.stop()
    assert not outbox.is_ready()


async def test_lifecycle_warns_for_missing_optional_dependencies(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(prepare_module, "otel_trace", None)
    runtime = ActivityRecordsOutbox(publisher=AsyncMock())

    with caplog.at_level(logging.WARNING, logger=enqueue_module.logger.name):
        with pytest.raises(ValueError):
            await runtime.start()

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 1
    assert any("opentelemetry" in message for message in messages)
    assert all("uv add opentelemetry-api" in message for message in messages)


async def test_runtime_drains_inserts_before_closing_the_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = asyncio.Event()

    class OrderedStore(Store):
        async def insert(self, rows: list[Any]) -> None:
            await super().insert(rows)
            wiring.calls.append("insert")

    wiring = patch_runtime(monkeypatch, OrderedStore(gate))
    outbox = new_outbox(Metrics())
    await outbox.start()
    enqueue(event())
    stopping = asyncio.create_task(outbox.stop())
    await asyncio.sleep(0)
    assert wiring.calls == ["relay.start", "relay.stop"]

    gate.set()
    await stopping

    assert wiring.calls == ["relay.start", "relay.stop", "insert", "pool.close"]
    assert outbox.publisher.mock_calls == []  # type: ignore[attr-defined]


async def test_start_failure_closes_the_pool_and_releases_the_outbox(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wiring = patch_runtime(
        monkeypatch, Store(), relay_error=RuntimeError("relay failed")
    )
    with pytest.raises(RuntimeError, match="relay failed"):
        await new_outbox(Metrics()).start()

    assert wiring.pools_closed == 1
    patch_runtime(monkeypatch, Store())
    await new_outbox(Metrics()).start()


async def test_stop_returns_when_the_pool_close_hangs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(enqueue_module, "POOL_CLOSE_TIMEOUT_SECONDS", 0.01)
    wiring = patch_runtime(monkeypatch, Store(), pool_close_hangs=True)
    outbox = new_outbox(Metrics())
    await outbox.start()

    await asyncio.wait_for(outbox.stop(), 2)

    assert wiring.pools_terminated == 1


async def test_a_failed_start_terminates_a_pool_that_will_not_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(enqueue_module, "POOL_CLOSE_TIMEOUT_SECONDS", 0.01)
    wiring = patch_runtime(
        monkeypatch,
        Store(),
        relay_error=RuntimeError("relay failed"),
        pool_close_hangs=True,
    )

    with pytest.raises(RuntimeError, match="relay failed"):
        await asyncio.wait_for(new_outbox(Metrics()).start(), 2)

    assert wiring.pools_terminated == 1


async def test_an_insert_that_never_finishes_is_counted_as_a_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(enqueue_module, "INSERT_TIMEOUT_SECONDS", 0.01)
    metrics = Metrics()
    await activate(monkeypatch, Store(asyncio.Event()), metrics)

    enqueue(event())
    await asyncio.wait_for(drain(), 2)

    assert metrics.value("unique_activity_event_outbox_record_failures_total") == 1
    assert "errorName=TimeoutError" in caplog.text


async def test_a_malformed_size_setting_fails_start_before_any_resource_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wiring = patch_runtime(monkeypatch, Store())
    monkeypatch.setenv("ACTIVITY_RECORDS_MAX_DATA_SIZE_BYTES", "not-a-number")

    with pytest.raises(ValueError):
        await new_outbox(Metrics()).start()

    assert wiring.relays == []
    monkeypatch.delenv("ACTIVITY_RECORDS_MAX_DATA_SIZE_BYTES")
    await new_outbox(Metrics()).start()


async def test_the_relay_gets_its_own_flag_client_when_none_is_injected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unique_toolkit.experimental.resources.feature_flags.client import (
        FeatureFlagClient,
    )

    monkeypatch.setenv("CONFIGURATION_BACKEND_URL", "http://configuration-backend")
    monkeypatch.setenv("FEATURE_FLAG_SERVICE_ID", "service")
    monkeypatch.setattr(FeatureFlagClient, "_instance", None)
    wiring = patch_runtime(monkeypatch, Store())
    outbox = ActivityRecordsOutbox(publisher=AsyncMock(), metrics=Metrics().metrics)
    _started.append(outbox)

    await outbox.start()

    (relay_client,) = wiring.relay_flag_clients
    shared = FeatureFlagClient.from_settings()
    assert isinstance(relay_client, FeatureFlagClient)
    assert relay_client is not shared


async def test_an_injected_flag_client_is_used_by_the_relay_as_well(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wiring = patch_runtime(monkeypatch, Store())
    flags = FlagClient(FlagEvaluation(value=True, reason="remote"))
    outbox = new_outbox(Metrics(), flags)

    await outbox.start()

    assert wiring.relay_flag_clients == [flags]


async def test_metadata_truncation_is_logged_with_field_names_only(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    await activate(monkeypatch, Store(), Metrics())
    built = ActivityCloudEvent.build(
        source="web-search",
        type="web-search.tool.called",
        data={"actor": {"id": "secret-" + "u" * 200, "type": "user"}, "companyId": "c"},
    )

    enqueue(built)
    await drain()

    messages = [r.getMessage() for r in caplog.records]
    assert any(
        "metadata field(s) truncated to fit their length limit" in m
        and "eventType=web-search.tool.called" in m
        and "source=web-search" in m
        and "metadataFields=['actor.id']" in m
        for m in messages
    )
    assert "secret-" not in caplog.text


async def test_missing_flag_settings_fail_start_with_a_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unique_toolkit.experimental.resources.feature_flags.client import (
        FeatureFlagClient,
    )

    monkeypatch.delenv("CONFIGURATION_BACKEND_URL", raising=False)
    monkeypatch.delenv("FEATURE_FLAG_SERVICE_ID", raising=False)
    monkeypatch.setattr(FeatureFlagClient, "_instance", None)
    wiring = patch_runtime(monkeypatch, Store())
    outbox = ActivityRecordsOutbox(publisher=AsyncMock(), metrics=Metrics().metrics)
    _started.append(outbox)

    with pytest.raises(ValueError, match="CONFIGURATION_BACKEND_URL"):
        await outbox.start()

    assert wiring.relays == []
