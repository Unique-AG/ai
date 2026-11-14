"""Best-effort Activity Records enqueueing and process lifecycle."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from unique_toolkit.experimental.resources.activity_records import (
    prepare as prepare_module,
)
from unique_toolkit.experimental.resources.activity_records.config import (
    DEFAULT_ACTIVITY_EVENTS_METRIC_NAME,
    FEATURE_FLAG_ENABLE_ACTIVITY_RECORDS_EVENTS_UN_22616,
    ActivityRecordsConfig,
)
from unique_toolkit.experimental.resources.activity_records.prepare import (
    OutboxRow,
    WireEvent,
    prepare_rows,
    to_last_error,
)
from unique_toolkit.experimental.resources.activity_records.protocols import (
    FlagClientLike,
    PublisherLike,
)
from unique_toolkit.experimental.resources.activity_records.relay import (
    OutboxRelay,
    count_events,
)
from unique_toolkit.experimental.resources.activity_records.schemas import (
    ActivityCloudEvent,
)

if TYPE_CHECKING:
    import asyncpg  # pyright: ignore[reportMissingImports]

    from unique_toolkit.experimental.resources.activity_records.metrics import (
        ActivityEventOutboxMetrics,
    )
    from unique_toolkit.experimental.resources.activity_records.store import OutboxStore

logger = logging.getLogger(__name__)

_DEFAULT_DRAIN_TIMEOUT_SECONDS = 10.0
_FIRST_FLAG_READ_TIMEOUT_SECONDS = 5.0
POOL_WAIT_TIMEOUT_SECONDS = 5
POOL_CLOSE_TIMEOUT_SECONDS = 5
# The pool's 10 s connect and 30 s command timeouts, so a waiting insert is bounded too.
INSERT_TIMEOUT_SECONDS = 40
WRITE_FLAG_FAILURE_COOLDOWN_SECONDS = 15
_pending_inserts: set[asyncio.Task[None]] = set()
_active_context: _EnqueueContext | None = None
# Kept after stop() so late enqueue calls still count in record_failures.
_last_metrics: ActivityEventOutboxMetrics | None = None


@dataclass(eq=False)
class _EnqueueContext:
    """What `enqueue` needs; `store_future` resolves once the pool exists."""

    metrics: ActivityEventOutboxMetrics
    flag_client: FlagClientLike
    max_data_size_bytes: int
    store_future: asyncio.Future[OutboxStore]
    flag_failed_until: dict[str, float] = field(default_factory=dict)


def _record_failure(
    metrics: ActivityEventOutboxMetrics | None,
    company_id: str,
    event_count: int,
    error: BaseException,
) -> None:
    if metrics is not None:
        metrics.record_failures.inc(event_count)
    logger.error(
        "Could not record activity events in the outbox; they are lost "
        "(companyId=%s eventCount=%s errorName=%s)",
        company_id,
        event_count,
        to_last_error(error),
    )


async def _close_pool(pool: asyncpg.Pool) -> None:
    """Close the pool, terminating it when a frozen database keeps ``close`` waiting."""
    try:
        await asyncio.wait_for(pool.close(), POOL_CLOSE_TIMEOUT_SECONDS)
    except TimeoutError:
        pool.terminate()


async def _flag_is_off(write: _EnqueueContext, company_id: str) -> bool:
    """True only for a fresh or cached off. After a failed read, skip reads for a while."""
    failed_until = write.flag_failed_until.get(company_id)
    if failed_until is not None:
        if time.monotonic() < failed_until:
            return False
        del write.flag_failed_until[company_id]
    try:
        evaluation = await asyncio.wait_for(
            write.flag_client.evaluate(
                FEATURE_FLAG_ENABLE_ACTIVITY_RECORDS_EVENTS_UN_22616,
                company_id=company_id,
            ),
            _FIRST_FLAG_READ_TIMEOUT_SECONDS,
        )
    except Exception as error:
        write.flag_failed_until[company_id] = (
            time.monotonic() + WRITE_FLAG_FAILURE_COOLDOWN_SECONDS
        )
        logger.warning(
            "Could not refresh the activity records flag (companyId=%s errorName=%s)",
            company_id,
            to_last_error(error),
        )
        return False
    return evaluation.value is False and evaluation.reason in ("remote", "cached")


async def _insert(
    write: _EnqueueContext,
    rows: list[OutboxRow],
    truncated_events: list[WireEvent],
    company_id: str,
) -> None:
    try:
        store = await asyncio.wait_for(
            asyncio.shield(write.store_future), POOL_WAIT_TIMEOUT_SECONDS
        )
        if await _flag_is_off(write, company_id):
            return
        await asyncio.wait_for(store.insert(rows), INSERT_TIMEOUT_SECONDS)
        if truncated_events:
            count_events(write.metrics, "truncated", truncated_events)
    except Exception as error:
        _record_failure(write.metrics, company_id, len(rows), error)


def enqueue(event: ActivityCloudEvent) -> None:
    """Prepare and enqueue one event from the event-loop thread without awaiting it."""
    company_id = event.data.company_id
    write = _active_context
    if write is None:
        if _last_metrics is not None:
            _last_metrics.record_failures.inc()
        logger.error(
            "Could not record an activity event: no Activity Records outbox is running "
            "(it is not started, or it is stopping); the event is lost (companyId=%s)",
            company_id,
        )
        return
    try:
        asyncio.get_running_loop()
        if event.truncated_fields:
            logger.warning(
                "Activity event metadata field(s) truncated to fit their length limit: "
                "eventType=%s source=%s metadataFields=%s",
                event.type,
                event.source,
                event.truncated_fields,
            )
        prepared = prepare_rows(company_id, [event], write.max_data_size_bytes)
        truncated_events = prepared.truncated_events
        if event.truncated_fields and not truncated_events:
            truncated_events = [prepared.rows[0].payload]
        task = asyncio.create_task(
            _insert(write, prepared.rows, truncated_events, company_id)
        )
        _pending_inserts.add(task)
        task.add_done_callback(_pending_inserts.discard)
    except Exception as error:
        _record_failure(write.metrics, company_id, 1, error)


async def drain(timeout: float = _DEFAULT_DRAIN_TIMEOUT_SECONDS) -> None:
    """Wait for currently scheduled inserts, leaving timed-out tasks running."""
    if not _pending_inserts:
        return
    pending = asyncio.gather(*_pending_inserts, return_exceptions=True)
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(asyncio.shield(pending), timeout)


class ActivityRecordsOutbox:
    """Own the database pool, relay, and enqueue lifecycle; the caller supplies the sender."""

    def __init__(
        self,
        *,
        publisher: PublisherLike,
        flag_client: FlagClientLike | None = None,
        metrics: ActivityEventOutboxMetrics | None = None,
        metric_name: str = DEFAULT_ACTIVITY_EVENTS_METRIC_NAME,
    ) -> None:
        self.publisher = publisher
        self.flag_client = flag_client
        self.metrics = metrics
        self.metric_name = metric_name
        self.pool: asyncpg.Pool | None = None
        self.relay: OutboxRelay | None = None
        self._write: _EnqueueContext | None = None

    async def start(self) -> None:
        """Create dependencies from environment and start the relay."""
        global _active_context, _last_metrics
        if self._write is not None:
            return
        if _active_context is not None:
            raise RuntimeError("Only one Activity Records outbox can be active")
        if prepare_module.otel_trace is None:
            logger.warning(
                "opentelemetry-api is not installed, so events get no correlationId from "
                "the active trace. Install it with: uv add opentelemetry-api"
            )
        settings = ActivityRecordsConfig()
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL is required for the Activity Records outbox")
        from unique_toolkit.experimental.resources.activity_records.metrics import (
            get_or_create_activity_event_outbox_metrics,
        )
        from unique_toolkit.experimental.resources.activity_records.store import (
            OutboxStore,
            create_pool,
        )
        from unique_toolkit.experimental.resources.feature_flags.client import (
            FeatureFlagClient,
        )
        from unique_toolkit.experimental.resources.feature_flags.settings import (
            FeatureFlagSettings,
        )

        flag_client = self.flag_client or FeatureFlagClient.from_settings()
        relay_flag_client = self.flag_client
        if relay_flag_client is None:
            # Own cache, or producers keep it warm and the relay never sees a remote read.
            # The client has no aclose(); one per process is accepted.
            flag_settings = FeatureFlagSettings()
            # from_settings() above already raised when either setting is missing.
            relay_flag_client = FeatureFlagClient(
                url=cast("str", flag_settings.configuration_backend_url),
                service_id=cast("str", flag_settings.feature_flag_service_id),
                ttl_ms=flag_settings.feature_flag_cache_ttl_ms,
            )
        metrics = self.metrics or get_or_create_activity_event_outbox_metrics(
            metric_name=self.metric_name
        )
        write = _EnqueueContext(
            metrics,
            flag_client,
            settings.max_data_size_bytes,
            asyncio.get_running_loop().create_future(),
        )
        pool = None
        _active_context = write
        _last_metrics = metrics
        try:
            pool = await create_pool(database_url, min_size=0, max_size=4)
            outbox_store = OutboxStore(pool)
            write.store_future.set_result(outbox_store)
            relay = OutboxRelay(
                outbox_store,
                self.publisher,
                relay_flag_client,
                metrics,
                max_batch_size_bytes=settings.max_batch_size_bytes,
                max_data_size_bytes=settings.max_data_size_bytes,
            )
            await relay.start()
        except BaseException:
            _active_context = None
            if pool is not None:
                await _close_pool(pool)
            raise
        self.pool, self.relay, self._write = pool, relay, write

    def is_ready(self) -> bool:
        return self.relay is not None and self.relay.is_ready()

    async def stop(self) -> None:
        """Stop delivery, drain inserts, then close the database pool."""
        global _active_context
        if _active_context is self._write:
            _active_context = None
        try:
            if self.relay is not None:
                await self.relay.stop()
            await drain()
        finally:
            try:
                if self.pool is not None:
                    await _close_pool(self.pool)
            finally:
                self.pool = None
                self.relay = None
                self._write = None
