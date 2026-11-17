"""Async relay for the Activity Records transactional outbox."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import operator
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, Literal
from uuid import uuid4

from unique_toolkit.experimental.resources.activity_records.config import (
    DEFAULT_MAX_BATCH_SIZE_BYTES,
    DEFAULT_MAX_DATA_SIZE_BYTES,
    FEATURE_FLAG_ENABLE_ACTIVITY_RECORDS_EVENTS_UN_22616,
    OUTBOX_MAX_BACKOFF_ATTEMPTS,
)
from unique_toolkit.experimental.resources.activity_records.prepare import (
    OutboxRow,
    split_into_batches_under_limit,
    to_last_error,
)
from unique_toolkit.experimental.resources.activity_records.protocols import (
    FlagClientLike,
    PublisherLike,
)
from unique_toolkit.experimental.resources.activity_records.schemas import (
    ActivityCloudEvent,
)

if TYPE_CHECKING:
    from unique_toolkit.experimental.resources.activity_records.metrics import (
        ActivityEventOutboxMetrics,
        PublishFailureReason,
    )
    from unique_toolkit.experimental.resources.activity_records.store import OutboxStore
    from unique_toolkit.experimental.resources.feature_flags.schemas import (
        FlagEvaluation,
    )

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RelayTimings:
    """Timing and batch limits for the relay."""

    idle_poll_seconds: float = 1.0
    claim_limit: int = 100
    lease_seconds: int = 90
    publish_timeout_seconds: float = 30.0
    flag_check_timeout_seconds: float = 5.0
    flag_unknown_defer_seconds: int = 30
    untried_defer_seconds: int = 5
    schema_recheck_seconds: float = 10.0
    stats_interval_seconds: float = 15.0
    stop_timeout_seconds: float = 5.0


# Mirrors Node OUTBOX_RELAY_TIMINGS.
OUTBOX_RELAY_TIMINGS: Final = RelayTimings()


FlagDecision = Literal["on", "off", "unknown"]


@dataclass(frozen=True, slots=True)
class _Claim:
    token: str
    ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Failure:
    reason: PublishFailureReason
    last_error: str


def _group_by_company(rows: Sequence[OutboxRow]) -> list[tuple[str, list[OutboxRow]]]:
    grouped: dict[str, list[OutboxRow]] = {}
    for row in rows:
        grouped.setdefault(row.company_id, []).append(row)
    return list(grouped.items())


def _event_labels(payload: Mapping[str, Any]) -> tuple[str, str, str]:
    data = payload.get("data", {})
    actor = data.get("actor", {}) if isinstance(data, Mapping) else {}
    return (
        str(payload.get("source", "")),
        str(actor.get("type", "")) if isinstance(actor, Mapping) else "",
        str(payload.get("type", "")),
    )


def count_events(
    metrics: ActivityEventOutboxMetrics,
    outcome: Literal["sent", "truncated"],
    events: Sequence[object],
) -> None:
    """Count events by the labels used by the Node client."""
    objects = [event for event in events if isinstance(event, Mapping)]
    for (source, actor_type, event_type), count in Counter(
        map(_event_labels, objects)
    ).items():
        metrics.events.labels(
            outcome=outcome,
            source=source,
            actorType=actor_type,
            eventType=event_type,
        ).inc(count)


class OutboxRelay:
    """Claims outbox rows, publishes them, and settles them with fenced writes."""

    def __init__(
        self,
        store: OutboxStore,
        publisher: PublisherLike,
        flag_client: FlagClientLike,
        metrics: ActivityEventOutboxMetrics,
        *,
        max_batch_size_bytes: int = DEFAULT_MAX_BATCH_SIZE_BYTES,
        max_data_size_bytes: int = DEFAULT_MAX_DATA_SIZE_BYTES,
    ) -> None:
        self.store = store
        self.publisher = publisher
        self.flag_client = flag_client
        self.metrics = metrics
        self.max_batch_size_bytes = max_batch_size_bytes
        self.max_data_size_bytes = max_data_size_bytes
        self._ready = False
        self._stopped = False
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._stats_task: asyncio.Task[None] | None = None
        self._active_claim: _Claim | None = None
        self._flag_unknown_until: dict[str, float] = {}
        self._schema_mismatch_reported = False
        self._database_unreachable_reported = False

    def is_ready(self) -> bool:
        return self._ready

    async def start(self) -> None:
        """Start the relay task; schema checks run in the background."""
        if self._task is not None and not self._task.done():
            return
        self._stopped = False
        self._ready = False
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Wait for the current round, then cancel it and release any active claim."""
        self._stopped = True
        self._ready = False
        self._stop_event.set()
        task, self._task = self._task, None
        stats_task, self._stats_task = self._stats_task, None
        try:
            if task is not None and not task.done():
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        asyncio.shield(task),
                        OUTBOX_RELAY_TIMINGS.stop_timeout_seconds,
                    )
        finally:
            running = [t for t in (task, stats_task) if t is not None]
            for running_task in running:
                running_task.cancel()
            # gather re-raises only a cancellation of the caller of stop().
            await asyncio.gather(*running, return_exceptions=True)
            await self._release_active_claim()

    async def refresh_stats(self) -> None:
        stats = await self.store.stats()
        self.metrics.pending_rows.set(stats.pending_rows)
        self.metrics.oldest_pending_age_seconds.set(stats.oldest_pending_age_seconds)
        self.metrics.rows_at_max_backoff.set(stats.rows_at_max_backoff)

    async def _check_flag(self, company_id: str) -> FlagDecision:
        """Return ``on``, ``off`` or ``unknown`` for one company."""
        unknown_until = self._flag_unknown_until.get(company_id)
        if unknown_until is not None and time.monotonic() < unknown_until:
            return "unknown"

        try:
            evaluation = await self._evaluate(company_id)
        except Exception as error:
            self._flag_unknown_until[company_id] = (
                time.monotonic() + OUTBOX_RELAY_TIMINGS.flag_unknown_defer_seconds / 2
            )
            self.metrics.flag_check_failures.inc()
            logger.warning(
                "Could not read the activity records flag; deferring the company’s "
                "outbox rows (companyId=%s errorName=%s)",
                company_id,
                to_last_error(error),
            )
            return "unknown"
        if evaluation.value:
            return "on"
        # Only a remote read may discard rows; a cached off waits for its entry to expire.
        return "off" if evaluation.reason == "remote" else "unknown"

    async def _evaluate(self, company_id: str) -> FlagEvaluation:
        evaluation = await asyncio.wait_for(
            self.flag_client.evaluate(
                FEATURE_FLAG_ENABLE_ACTIVITY_RECORDS_EVENTS_UN_22616,
                company_id=company_id,
            ),
            OUTBOX_RELAY_TIMINGS.flag_check_timeout_seconds,
        )
        if evaluation.reason == "fallback" or (
            evaluation.reason == "stale" and not evaluation.value
        ):
            raise RuntimeError("fallback")
        return evaluation

    def _build_messages(self, rows: Sequence[OutboxRow]) -> list[list[OutboxRow]]:
        """Validate rows and group valid payloads under the batch-size limit."""
        messages: list[list[OutboxRow]] = []
        for company_id, company_rows in _group_by_company(rows):
            valid: list[OutboxRow] = []
            for row in company_rows:
                try:
                    ActivityCloudEvent.from_wire(row.payload)
                except Exception:
                    self.metrics.invalid_events.inc()
                    logger.warning(
                        "An outbox event fails the activity event schema; sending it "
                        "in a message of its own (companyId=%s source=%s)",
                        company_id,
                        row.source,
                    )
                    messages.append([row])
                else:
                    valid.append(row)
            messages.extend(
                split_into_batches_under_limit(
                    valid,
                    operator.attrgetter("payload"),
                    self.max_batch_size_bytes,
                    self.max_data_size_bytes,
                )
            )
        return messages

    async def _run_loop(self) -> None:
        next_schema = time.monotonic()
        while not self._stopped:
            if not self._ready:
                delay = max(0.0, next_schema - time.monotonic())
                if await self._wait_for_stop(delay):
                    return
                self._ready = await self._check_schema()
                next_schema = (
                    time.monotonic() + OUTBOX_RELAY_TIMINGS.schema_recheck_seconds
                )
                if self._ready and self._stats_task is None:
                    self._stats_task = asyncio.create_task(self._stats_loop())
                continue

            try:
                settled = await self.run_once()
            except Exception as error:
                logger.error(
                    "Activity event outbox relay iteration failed (%s)",
                    to_last_error(error),
                )
                settled = 0

            delay = (
                0
                if settled >= OUTBOX_RELAY_TIMINGS.claim_limit
                else OUTBOX_RELAY_TIMINGS.idle_poll_seconds
            )
            if await self._wait_for_stop(delay):
                return

    async def _stats_loop(self) -> None:
        """Refresh the gauges on their own timer, like Node, so a long round does not delay them."""
        while not await self._wait_for_stop(
            OUTBOX_RELAY_TIMINGS.stats_interval_seconds
        ):
            try:
                await self.refresh_stats()
            except Exception as error:
                logger.warning(
                    "Could not refresh the activity event outbox gauges (%s)",
                    to_last_error(error),
                )

    async def _wait_for_stop(self, delay: float) -> bool:
        if self._stop_event.is_set():
            return True
        try:
            await asyncio.wait_for(self._stop_event.wait(), delay)
        except TimeoutError:
            return False
        return True

    async def _check_schema(self) -> bool:
        try:
            matches = await self.store.has_expected_columns()
        except Exception as error:
            if not self._stopped and not self._database_unreachable_reported:
                self._database_unreachable_reported = True
                logger.warning(
                    "The database is unreachable, so the ActivityEventOutbox table "
                    "cannot be verified; staying unready and retrying (errorName=%s)",
                    to_last_error(error),
                )
            return False
        self._database_unreachable_reported = False
        if self._stopped:
            return False
        if not matches:
            if not self._schema_mismatch_reported:
                self._schema_mismatch_reported = True
                logger.error(
                    "The ActivityEventOutbox table is missing or its columns differ "
                    "from ACTIVITY_EVENT_OUTBOX_COLUMNS; staying unready until the "
                    "migration has run",
                )
            return False
        logger.info(
            "ActivityEventOutbox table verified; starting the activity event outbox relay",
        )
        return True

    async def run_once(self) -> int:
        """Run one claim round and return rows delivered, discarded, or backed off."""
        claim_token = str(uuid4())
        deadline = time.monotonic() + OUTBOX_RELAY_TIMINGS.lease_seconds / 2
        rows = await self.store.claim(
            claim_token,
            OUTBOX_RELAY_TIMINGS.claim_limit,
            OUTBOX_RELAY_TIMINGS.lease_seconds,
        )
        if not rows:
            return 0

        claim = _Claim(claim_token, tuple(row.id for row in rows))
        self._active_claim = claim
        try:
            return await self._settle_claim(claim_token, rows, deadline)
        finally:
            await self._release_claim(claim)
            if self._active_claim == claim:
                self._active_claim = None

    async def _settle_claim(
        self, claim_token: str, rows: Sequence[OutboxRow], deadline: float
    ) -> int:
        self._sweep_unknown_flags()
        companies = _group_by_company(rows)
        decisions = await asyncio.gather(
            *(self._check_flag(company_id) for company_id, _ in companies)
        )
        settled = 0
        deliverable: list[OutboxRow] = []
        for (company_id, company_rows), decision in zip(companies, decisions):
            ids = [row.id for row in company_rows]
            if decision == "off":
                deleted = await self.store.delete_claimed(claim_token, ids)
                settled += len(deleted)
                self.metrics.discarded.inc(len(deleted))
                logger.info(
                    "Deleted outbox events of a company whose activity records flag is off "
                    "(companyId=%s eventCount=%s)",
                    company_id,
                    len(deleted),
                )
            elif decision == "unknown":
                await self.store.defer(
                    claim_token,
                    ids,
                    OUTBOX_RELAY_TIMINGS.flag_unknown_defer_seconds,
                )
            else:
                deliverable.extend(company_rows)

        settled += await self._publish_messages(
            claim_token, self._build_messages(deliverable), deadline
        )
        return settled

    async def _publish_messages(
        self, claim_token: str, messages: Sequence[list[OutboxRow]], deadline: float
    ) -> int:
        settled = 0
        for index, message in enumerate(messages):
            if not self._may_publish(deadline):
                return settled
            failure = await self._publish(message)
            if failure is None:
                settled += await self._settle_delivered(claim_token, message)
                continue
            if self._stopped:
                return settled

            if failure.reason == "timeout":
                settled += await self._back_off(
                    claim_token, message, failure.last_error
                )
                await self._defer_untried(
                    claim_token,
                    [row for rest in messages[index + 1 :] for row in rest],
                )
                return settled

            if len(message) == 1:
                settled += await self._back_off(
                    claim_token, message, failure.last_error
                )
                continue

            for row_index, row in enumerate(message):
                if not self._may_publish(deadline):
                    return settled
                single_failure = await self._publish([row])
                if single_failure is None:
                    settled += await self._settle_delivered(claim_token, [row])
                    continue
                if self._stopped:
                    return settled
                if single_failure.reason == "timeout":
                    settled += await self._back_off(
                        claim_token, [row], single_failure.last_error
                    )
                    await self._defer_untried(
                        claim_token,
                        [
                            *message[row_index + 1 :],
                            *[item for rest in messages[index + 1 :] for item in rest],
                        ],
                    )
                    return settled
                settled += await self._back_off(
                    claim_token, [row], single_failure.last_error
                )
        return settled

    async def _publish(self, rows: Sequence[OutboxRow]) -> _Failure | None:
        try:
            await asyncio.wait_for(
                self.publisher.publish([row.payload for row in rows]),
                OUTBOX_RELAY_TIMINGS.publish_timeout_seconds,
            )
        except Exception as error:
            reason = "timeout" if isinstance(error, TimeoutError) else "rejected"
            # After stop() the shutdown cut the publish off, and stop() hands its rows back.
            if not self._stopped:
                self.metrics.publish_failures.labels(reason=reason).inc()
            return _Failure(reason, to_last_error(error))
        return None

    async def _settle_delivered(
        self, claim_token: str, rows: Sequence[OutboxRow]
    ) -> int:
        ids = [row.id for row in rows]
        deleted = set(await self.store.delete_claimed(claim_token, ids))
        delivered = [row.payload for row in rows if row.id in deleted]
        if delivered:
            count_events(self.metrics, "sent", delivered)
        return len(deleted)

    async def _back_off(
        self, claim_token: str, rows: Sequence[OutboxRow], last_error: str
    ) -> int:
        attempts = await self.store.reschedule_with_backoff(
            claim_token,
            [row.id for row in rows],
            last_error,
        )
        reached_max = attempts.count(OUTBOX_MAX_BACKOFF_ATTEMPTS)
        if reached_max:
            self.metrics.backoff_max_reached.inc(reached_max)
        logger.warning(
            "Activity event outbox publish failed; backing off "
            "(eventCount=%s lastError=%s)",
            len(rows),
            last_error,
        )
        return len(attempts)

    async def _defer_untried(self, claim_token: str, rows: Sequence[OutboxRow]) -> None:
        if rows:
            await self.store.defer(
                claim_token,
                [row.id for row in rows],
                OUTBOX_RELAY_TIMINGS.untried_defer_seconds,
            )

    def _may_publish(self, deadline: float) -> bool:
        return not self._stopped and time.monotonic() < deadline

    def _sweep_unknown_flags(self) -> None:
        now = time.monotonic()
        for company_id, until in list(self._flag_unknown_until.items()):
            if until <= now:
                del self._flag_unknown_until[company_id]

    async def _release_active_claim(self) -> None:
        claim = self._active_claim
        if claim is None:
            return
        self._active_claim = None
        await self._release_claim(claim)

    async def _release_claim(self, claim: _Claim) -> None:
        try:
            await asyncio.shield(self.store.defer(claim.token, list(claim.ids), 0))
        except Exception as error:
            logger.warning(
                "Could not hand back claimed outbox rows; they return when the lease "
                "expires (%s)",
                to_last_error(error),
            )
