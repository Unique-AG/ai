from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

asyncpg = pytest.importorskip(
    "asyncpg",
    reason="Activity Records Docker tests need the activity-records extra",
)

from unique_toolkit.experimental.resources.activity_records import (  # noqa: E402
    ActivityActor,
    ActivityCloudEvent,
    ActivityEventData,
)
from unique_toolkit.experimental.resources.activity_records.config import (  # noqa: E402
    DEFAULT_MAX_DATA_SIZE_BYTES,
)
from unique_toolkit.experimental.resources.activity_records.json_size import (  # noqa: E402
    json_byte_length,
)
from unique_toolkit.experimental.resources.activity_records.prepare import (  # noqa: E402
    OutboxRow,
    prepare_rows,
)
from unique_toolkit.experimental.resources.activity_records.store import (  # noqa: E402
    ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL,
    OutboxStore,
    create_pool,
)

from .conftest import docker_container, wait_until  # noqa: E402

pytestmark = pytest.mark.ai


@pytest.fixture(scope="module")
def dsn(docker_tests: None) -> Iterator[str]:
    with docker_container("postgres:17-alpine", 5432, "POSTGRES_PASSWORD=pw") as (
        _postgres,
        port,
    ):
        url = f"postgresql://postgres:pw@127.0.0.1:{port}/postgres"
        asyncio.run(wait_until(lambda: asyncpg.connect(url), 60))
        yield url


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
async def _resources(dsn: str) -> AsyncIterator[SimpleNamespace]:
    pool = await create_pool(dsn, min_size=1, max_size=8)
    await pool.execute('DROP TABLE IF EXISTS "ActivityEventOutbox"')
    await pool.execute(ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL)
    try:
        yield SimpleNamespace(pool=pool, store=OutboxStore(pool))
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
