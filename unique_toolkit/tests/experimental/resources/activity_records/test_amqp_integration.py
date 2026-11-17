"""The outbox delivering through AmqpPublisher to a RabbitMQ container, backed by Postgres."""

from __future__ import annotations

import asyncio
import json

import pytest

aio_pika = pytest.importorskip(
    "aio_pika",
    reason="Activity Records Docker tests need the activity-records-amqp extra",
)

from prometheus_client import CollectorRegistry  # noqa: E402

from unique_toolkit.experimental.resources.activity_records import (  # noqa: E402
    ActivityActor,
    ActivityCloudEvent,
    ActivityEventData,
    ActivityRecordsOutbox,
    drain,
    enqueue,
)
from unique_toolkit.experimental.resources.activity_records.metrics import (  # noqa: E402
    get_or_create_activity_event_outbox_metrics,
)
from unique_toolkit.experimental.resources.activity_records.publishers.amqp_publisher import (  # noqa: E402
    ROUTING_KEY,
    AmqpPublisher,
)
from unique_toolkit.experimental.resources.activity_records.store import (  # noqa: E402
    ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL,
    create_pool,
)
from unique_toolkit.experimental.resources.feature_flags.schemas import (  # noqa: E402
    FlagEvaluation,
)

from .conftest import Flags  # noqa: E402

pytestmark = pytest.mark.ai


async def test_enqueued_event_reaches_the_queue_and_the_row_is_deleted(
    dsn: str, rabbitmq: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    amqp_url, _container = rabbitmq
    monkeypatch.setenv("DATABASE_URL", dsn)
    monkeypatch.setenv("AMQP_URL", amqp_url)
    pool = await create_pool(dsn, min_size=1, max_size=2)
    await pool.execute(ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL)
    consumer = await aio_pika.connect(amqp_url)
    channel = await consumer.channel()
    queue = await channel.declare_queue(ROUTING_KEY, durable=True)
    publisher = AmqpPublisher()
    outbox = ActivityRecordsOutbox(
        publisher=publisher,
        flag_client=Flags(FlagEvaluation(value=True, reason="remote")),
        metrics=get_or_create_activity_event_outbox_metrics(
            registry=CollectorRegistry()
        ),
    )
    event = ActivityCloudEvent(
        source="integration-test",
        type="activity.test",
        data=ActivityEventData(
            actor=ActivityActor(id="user", type="user"),
            company_id="company-1",
        ),
    )
    await publisher.connect()
    await outbox.start()
    try:
        enqueue(event)
        await drain()
        incoming = None
        for _ in range(300):
            incoming = await queue.get(fail=False, no_ack=True)
            if incoming is not None:
                break
            await asyncio.sleep(0.1)
        assert incoming is not None, "the event was not published"
        remaining = -1
        for _ in range(50):
            remaining = await pool.fetchval(
                'SELECT count(*) FROM "ActivityEventOutbox"'
            )
            if remaining == 0:
                break
            await asyncio.sleep(0.1)
    finally:
        await outbox.stop()
        await publisher.close()
        await consumer.close()
        await pool.close()

    assert [item["id"] for item in json.loads(incoming.body)] == [str(event.id)]
    assert remaining == 0
