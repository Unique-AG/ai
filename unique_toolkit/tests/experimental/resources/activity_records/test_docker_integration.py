from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

asyncpg = pytest.importorskip(
    "asyncpg",
    reason="Activity Records Docker tests need the activity-records extra",
)
pytest.importorskip(
    "prometheus_client",
    reason="Activity Records Docker tests need the activity-records extra",
)

from prometheus_client import CollectorRegistry  # noqa: E402

from unique_toolkit.experimental.resources.activity_records import (  # noqa: E402
    ActivityActor,
    ActivityCloudEvent,
    ActivityEventData,
    ActivityRecordsOutbox,
)
from unique_toolkit.experimental.resources.activity_records.config import (  # noqa: E402
    DEFAULT_MAX_DATA_SIZE_BYTES,
)
from unique_toolkit.experimental.resources.activity_records.enqueue import (  # noqa: E402
    drain,
    enqueue,
)
from unique_toolkit.experimental.resources.activity_records.json_size import (  # noqa: E402
    json_byte_length,
)
from unique_toolkit.experimental.resources.activity_records.metrics import (  # noqa: E402
    get_or_create_activity_event_outbox_metrics,
)
from unique_toolkit.experimental.resources.activity_records.prepare import (  # noqa: E402
    OutboxRow,
    prepare_rows,
)
from unique_toolkit.experimental.resources.activity_records.relay import (  # noqa: E402
    OUTBOX_RELAY_TIMINGS,
    OutboxRelay,
)
from unique_toolkit.experimental.resources.activity_records.store import (  # noqa: E402
    ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL,
    OutboxStore,
    create_pool,
)
from unique_toolkit.experimental.resources.feature_flags.schemas import (  # noqa: E402
    FlagEvaluation,
)

from .conftest import docker_container, wait_until  # noqa: E402

pytestmark = pytest.mark.ai

_ON = FlagEvaluation(value=True, reason="remote")


@pytest.fixture(scope="module")
def dsn(docker_tests: None) -> Iterator[str]:
    with docker_container("postgres:17-alpine", 5432, "POSTGRES_PASSWORD=pw") as (
        _postgres,
        port,
    ):
        url = f"postgresql://postgres:pw@127.0.0.1:{port}/postgres"
        asyncio.run(wait_until(lambda: asyncpg.connect(url), 60))
        yield url


class Flags:
    def __init__(self, evaluation: FlagEvaluation) -> None:
        self.evaluation = evaluation

    async def evaluate(self, _flag: str, *, company_id: str) -> FlagEvaluation:
        assert company_id
        return self.evaluation


class RecordingPublisher:
    """Records every batch it is given; raises ``error`` when one is set."""

    def __init__(self) -> None:
        self.batches: list[list[dict[str, Any]]] = []
        self.error: Exception | None = None

    async def publish(self, events: list[dict[str, Any]]) -> None:
        if self.error is not None:
            raise self.error
        self.batches.append(list(events))

    @property
    def ids(self) -> list[str]:
        return [event["id"] for batch in self.batches for event in batch]


def _event(company_id: str = "company-1") -> ActivityCloudEvent:
    return ActivityCloudEvent(
        source="integration-test",
        type="activity.test",
        time=datetime.now(UTC),
        data=ActivityEventData(
            actor=ActivityActor(id="user", type="user"),
            company_id=company_id,
        ),
    )


@asynccontextmanager
async def _resources(
    dsn: str, flag: FlagEvaluation = _ON
) -> AsyncIterator[SimpleNamespace]:
    pool = await create_pool(dsn, min_size=1, max_size=8)
    await pool.execute('DROP TABLE IF EXISTS "ActivityEventOutbox"')
    await pool.execute(ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL)
    store = OutboxStore(pool)
    publisher = RecordingPublisher()
    metrics = get_or_create_activity_event_outbox_metrics(registry=CollectorRegistry())
    relay = OutboxRelay(store, publisher, Flags(flag), metrics)
    try:
        yield SimpleNamespace(
            pool=pool, store=store, publisher=publisher, relay=relay, metrics=metrics
        )
    finally:
        await pool.close()


async def _insert(store: OutboxStore, *events: ActivityCloudEvent) -> None:
    await store.insert(
        [
            OutboxRow(
                str(event.id), event.data.company_id, event.source, event.to_wire()
            )
            for event in events
        ]
    )


async def _row_count(pool: Any) -> int:
    return await pool.fetchval('SELECT count(*) FROM "ActivityEventOutbox"')


async def test_relay_publishes_and_deletes(dsn: str) -> None:
    async with _resources(dsn) as resources:
        item = _event()
        await _insert(resources.store, item)

        assert await resources.relay.run_once() == 1

        assert resources.publisher.ids == [str(item.id)]
        assert resources.publisher.batches[0][0]["source"] == "integration-test"
        assert await _row_count(resources.pool) == 0


async def test_rejected_publish_keeps_the_row_with_a_backoff(dsn: str) -> None:
    async with _resources(dsn) as resources:
        await _insert(resources.store, _event())
        resources.publisher.error = RuntimeError("rejected")

        await resources.relay.run_once()

        row = await resources.pool.fetchrow(
            'SELECT "attempts", "claimToken", "nextAttemptAt" > now() AS later '
            'FROM "ActivityEventOutbox"'
        )
        assert (row["attempts"], row["claimToken"], row["later"]) == (1, None, True)


async def test_outbox_lifecycle_with_an_injected_publisher(
    dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with _resources(dsn) as resources:
        monkeypatch.setenv("DATABASE_URL", dsn)
        runtime = ActivityRecordsOutbox(
            publisher=resources.publisher,
            flag_client=Flags(_ON),
            metrics=resources.metrics,
        )
        await runtime.start()
        try:
            for _ in range(20):
                if runtime.is_ready():
                    break
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("outbox did not become ready")

            item = _event()
            enqueue(item)
            await drain()
            for _ in range(50):
                if resources.publisher.ids:
                    break
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("outbox did not deliver the event")
            assert resources.publisher.ids == [str(item.id)]
        finally:
            await runtime.stop()


async def test_flag_off_deletes_and_unknown_keeps_rows(dsn: str) -> None:
    async with _resources(dsn, FlagEvaluation(value=False, reason="remote")) as off:
        await _insert(off.store, _event())
        assert await off.relay.run_once() == 1
        assert off.publisher.batches == []
        assert (await off.store.stats()).pending_rows == 0

    async with _resources(
        dsn, FlagEvaluation(value=False, reason="fallback")
    ) as unknown:
        await _insert(unknown.store, _event())
        assert await unknown.relay.run_once() == 0
        assert unknown.publisher.batches == []
        assert (await unknown.store.stats()).pending_rows == 1


async def test_two_relays_claim_disjoint_rows(dsn: str) -> None:
    async with _resources(dsn) as first:
        second_publisher = RecordingPublisher()
        second = OutboxRelay(first.store, second_publisher, Flags(_ON), first.metrics)
        events = [_event() for _ in range(6)]
        await _insert(first.store, *events)

        await asyncio.gather(first.relay.run_once(), second.run_once())

        ids = first.publisher.ids + second_publisher.ids
        assert sorted(ids) == sorted(str(event.id) for event in events)
        assert await _row_count(first.pool) == 0


async def test_a_lapsed_lease_is_reclaimed_after_a_crash(dsn: str) -> None:
    async with _resources(dsn) as resources:
        item = _event()
        await _insert(resources.store, item)
        crashed = await resources.store.claim(str(uuid4()), 100, 1)
        assert [row.id for row in crashed] == [str(item.id)]

        assert await resources.relay.run_once() == 0
        await asyncio.sleep(1.2)
        assert await resources.relay.run_once() == 1

        assert resources.publisher.ids == [str(item.id)]
        assert await _row_count(resources.pool) == 0


async def test_floats_keep_the_payload_under_the_cap_after_the_jsonb_round_trip(
    dsn: str,
) -> None:
    async with _resources(dsn) as resources:
        event = ActivityCloudEvent(
            source="integration-test",
            type="activity.test",
            data=ActivityEventData(
                actor=ActivityActor(id="user", type="user"),
                company_id="company-1",
                critical_data={"values": [2.5e20] * 60_000},
            ),
        )
        (row,) = prepare_rows("company-1", [event], DEFAULT_MAX_DATA_SIZE_BYTES).rows
        await resources.store.insert([row])

        (claimed,) = await resources.store.claim(str(uuid4()), 100, 90)

        assert claimed.payload["data"]["criticalData"]["truncated"] is True
        assert json_byte_length(claimed.payload["data"]) <= DEFAULT_MAX_DATA_SIZE_BYTES


async def test_stop_hands_a_claim_back(
    dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "unique_toolkit.experimental.resources.activity_records.relay.OUTBOX_RELAY_TIMINGS",
        replace(OUTBOX_RELAY_TIMINGS, stop_timeout_seconds=0.01),
    )
    async with _resources(dsn) as resources:
        started = asyncio.Event()

        class BlockingPublisher:
            async def publish(self, _events: list[dict[str, Any]]) -> None:
                started.set()
                await asyncio.Event().wait()

        item = _event()
        await _insert(resources.store, item)
        relay = OutboxRelay(
            resources.store, BlockingPublisher(), Flags(_ON), resources.metrics
        )
        await relay.start()
        await asyncio.wait_for(started.wait(), 1)
        await relay.stop()

        assert (
            await resources.pool.fetchval(
                'SELECT "claimToken" FROM "ActivityEventOutbox" WHERE "id" = $1::uuid',
                str(item.id),
            )
            is None
        )
