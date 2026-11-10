# Activity Records outbox
This library records validated Activity Records events in the producer's own
Postgres database and relays them through a sender the caller supplies. It
prepares events synchronously, stores them in a background task, and retries
failed deliveries. Rows are deleted only after the sender returns without raising,
or when the flag client's remote read says the company is off. A cached off defers
the rows until the cache expires and a remote read answers.

```text
enqueue(event) -> ActivityEventOutbox table -> OutboxRelay -> sender
```

This is a port of the Node `@unique/activity-events-client` as on its master
branch: PR #33463 (merged) plus the follow-up #34009. It is experimental and
the interface may change.

## Install
```sh
uv add 'unique-toolkit[activity-records]'
```

The extra installs asyncpg and prometheus_client. Also install `opentelemetry-api`
(or the `otel` extra) so events get their correlationId from the active trace.

## Migration
Run the idempotent migration before the application starts:

```sh
python -m unique_toolkit.experimental.resources.activity_records.migrate
```

`DATABASE_URL` is required. The command exits non-zero, with a message that names the
table and no values, when the table exists but a column is missing or has a wrong
type. Extra columns are allowed. Run this command from a Helm
`pre-install,pre-upgrade` hook, not from application startup.

## Configuration
Required database variable:

- `DATABASE_URL`: asyncpg reads its query parameters. `sslmode=verify` becomes
  `verify-full` and `connect_timeout` becomes the connect timeout. `application_name`
  is kept. Any other parameter asyncpg does not read, such as Prisma's `schema=` or
  `connection_limit=`, is dropped and only its name is logged once.

Size settings are `ACTIVITY_RECORDS_MAX_DATA_SIZE_BYTES` and
`ACTIVITY_RECORDS_MAX_BATCH_SIZE_BYTES`, defaulting to 1 MiB and 8 MiB.

The default feature flag client needs `CONFIGURATION_BACKEND_URL`,
`FEATURE_FLAG_SERVICE_ID`, and optionally `FEATURE_FLAG_CACHE_TTL_MS`. The flag
is `FEATURE_FLAG_ENABLE_ACTIVITY_RECORDS_EVENTS_UN_22616`. Keep
`FEATURE_FLAG_CACHE_TTL_MS` at 5000 or less, because the write path skips an insert
on a cached off. When no flag client is injected, the write path uses the shared
`FeatureFlagClient` and the relay builds its own instance from the same settings.
The relay needs its own cache: callers that keep the shared cache warm would hide
every remote read, and only a remote off deletes rows. An injected flag client is
used for both, so it must not share a cache that other callers keep warm.

## Sender
Delivery is done by a sender the caller supplies (`PublisherLike`):
`async publish(events: list[dict]) -> None`. Raise a `TimeoutError` subclass on
timeout. Any other exception means rejected and the row backs off. The caller
owns the sender's connection. The GraphQL sender lands with UN-29210.

## FastAPI
Create one runtime and start and stop it in the FastAPI lifespan:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from unique_toolkit.experimental.resources.activity_records import ActivityRecordsOutbox

runtime = ActivityRecordsOutbox(publisher=my_sender)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    await runtime.start()
    try:
        yield
    finally:
        await runtime.stop()

app = FastAPI(lifespan=lifespan)
```

Use `runtime.is_ready()` for the service readiness probe. It answers false until
the relay's schema check passes, then stays true, also while the database is down
(the relay keeps polling and logs the errors). The check re-runs every 10 seconds,
like Node. An error during the check is logged once per outage as an
unreachable database, and only a real column mismatch is logged as a missing table.

## Enqueue an event
```python
from unique_toolkit.experimental.resources.activity_records import (
    ActivityActor,
    ActivityCloudEvent,
    ActivityEventData,
    enqueue,
)

event = ActivityCloudEvent(
    source="web-search",
    type="web-search.tool.called",
    data=ActivityEventData(
        actor=ActivityActor(id="user-1", type="user"),
        company_id="company-1",
    ),
)
enqueue(event)
```

The constructor rejects metadata over its length limit (identifier 128, ip 64,
text 256 UTF-16 units). `ActivityCloudEvent.build(source=..., type=..., data={...})`
shortens such values instead, so a long name never drops the record. It counts
the event as `truncated`, lists the fields in `event.truncated_fields` and logs a
warning with the event type, the source and the field paths (never the values).
The paths are wire paths like Node's, for example `actor.id`, `agent.id` and `targetName`.
Producers should build events with `build`.

`enqueue` is synchronous for the caller and never raises. Call it from the
event-loop thread. Preparing an event (validation, sizing, truncation) is CPU bound
and runs synchronously on the event loop, like Node's. It is best effort:
the prepared insert runs in a background task, and normal shutdown drains
pending inserts for up to 10 seconds. Delivery is at least once. The insert
does not wait for the relay's table check; a missing or mismatched table fails
the insert and counts a record failure. It waits at most 5 seconds for the
database pool to exist. Waiting for a free connection is bounded by the 40 second
insert timeout. `enqueue` skips the insert when a fresh or cached flag read says
off. After a failed flag read (including the 5 second timeout) a company is not
asked again for 15 seconds and its events are inserted; the relay checks the
flag again before delivery and defers when it is unknown.

Events are lost, and counted in `record_failures`, when the insert fails. A refused
connection loses the event at once. The 5 seconds cover only the wait for the
database pool. An insert on a frozen database fails after at most 40 seconds (10
seconds to connect and 30 seconds per command; the insert call is limited to 40
seconds). Events are also lost when the process exits before the background
insert runs (not counted). An `enqueue` call while no outbox is running (before
`start()`, or while `stop()` runs) logs "no Activity Records outbox is running" and
counts in `record_failures` once an outbox has run in the process.

When the flag is off at `enqueue`, the insert is skipped without a metric or a log,
like Node's best effort write. The 15 second pause on flag reads starts only when the
5 second wait expires or the flag client raises. The default flag client never
raises: when a request fails or exceeds its own 2 second timeout (1 second to
connect) it returns a fallback or stale answer, which
the write path treats as unknown and inserts the event.

## criticalData size limit
An event's `data` may not exceed `ACTIVITY_RECORDS_MAX_DATA_SIZE_BYTES` (1 MiB by
default). When it does, `criticalData` is cut to fit: strings are shortened, keys
and array items can be dropped, and `criticalData.truncated` is set to true. The
event is counted as `truncated`. A value nested deeper than 200 levels is cut the same
way: the part below that depth becomes null and `criticalData.truncated` marks it too.

## Kill switch
When the relay reads a company's flag as off from the remote, it deletes that
company's queued rows without publishing them and counts them in
`unique_activity_event_outbox_discarded_total`. This also hits events recorded while
the flag was on. The configuration backend answers false for a flag key it does not
know, so a flag key that does not exist reads as off and deletes every queued event
of every company. Roll out in this order: release the code that reads the flag,
create the flag, and only then enable it. To retire the flag, remove the flag check
from the service first and the key from the registry afterwards.

## Personal data in the outbox
The `payload` column holds the full event, including `criticalData` (for web search
the user prompt and the tool arguments). It is a second store of personal data and
is not covered by the data redaction job. A healthy outbox holds seconds of it. A
stuck row stays until it is delivered. Company deletion does not purge outbox rows.

## Rolling back
A rollback never removes the table. Queued rows stay, and nothing delivers them
while the service runs without this library. Wait for
`unique_activity_event_outbox_pending_rows` to reach 0 before rolling back.

## Settings
`ACTIVITY_RECORDS_MAX_DATA_SIZE_BYTES` and `ACTIVITY_RECORDS_MAX_BATCH_SIZE_BYTES`
are read by the activity-records intake too. If you override either, override it on
both sides. A missing value uses the default and a numeric string is accepted. A
value that is not a number, or a batch size too small for the data size, makes
`start()` raise before anything is created, like Node's assert at construction.

The relay's timings are fixed, like Node's. It claims up to 100 rows under a 90
second lease and publishes nothing after half of it. It polls every second when idle
and waits 5 seconds for a flag answer and 30 seconds for the sender. Rows whose flag
cannot be read are deferred by 15 to 30 seconds (30 seconds with 50 to 100 percent
jitter), and that company is not asked again for 15 seconds. Gauges refresh every 15
seconds and keep their last value if a refresh fails. The relay claims again at once
only after settling a full batch; a round that only deferred rows waits the idle
poll. On shutdown the relay stops and hands its rows back, then pending inserts get
10 seconds, then the pool closes (terminated after 5 seconds if the database does
not answer).

## Alerts
The Helm library chart `charts/activity-events-client` ships the alerts for the
outbox metrics. A service that uses this library includes that chart and sets
`activityEventsClient.metricName` to the `metric_name` used in code (default
`unique_activity_events_total`). Keep `tableAlerts` true on exactly one deployable
per outbox table. The backoff cap alert is critical. Do not write alerts on these
metrics by hand in `prometheus.additionalAlerts`, because the chart already renders
them and a copy fires twice. Add the chart directory to the service's CI path
filters and sparse checkout. The alert texts mention RabbitMQ today; read it as the
sender. A `timeout` publish failure means the sender raised a `TimeoutError` or took
longer than 30 seconds, and `rejected` means any other exception.
The alert texts need new wording when the GraphQL sender replaces RabbitMQ.

## Readiness and migration
Run the migration as a Helm pre-install and pre-upgrade hook so there is no deploy
order problem. Extra columns are allowed, so a rollback onto a newer migration keeps
working. Until the schema check passes the relay does not run and `is_ready()` is
false.

## Metrics
- `unique_activity_events_total{outcome,source,actorType,eventType}`
- `unique_activity_event_outbox_record_failures_total`
- `unique_activity_event_outbox_publish_failures_total{reason}`
- `unique_activity_event_outbox_backoff_max_reached_total`
- `unique_activity_event_outbox_discarded_total`
- `unique_activity_event_outbox_invalid_events_total`
- `unique_activity_event_outbox_flag_check_failures_total`
- `unique_activity_event_outbox_pending_rows`
- `unique_activity_event_outbox_oldest_pending_age_seconds`
- `unique_activity_event_outbox_rows_at_max_backoff`

The metrics use the toolkit's private registry. The host must serve
`unique_toolkit.monitoring.get_metrics()` on the `/metrics` path that Prometheus
scrapes. The three gauges (`pending_rows`, `oldest_pending_age_seconds`, `rows_at_max_backoff`)
are table-wide, so every worker reports the same value; in multiprocess mode they use
`livemax` to keep one series. Publish failure reasons are `timeout` and `rejected`. A publish that fails while
the relay is stopping is neither counted nor backed off, because `stop()` hands the
rows back. A sender call that takes longer than 30 seconds counts as a timeout. A
rejected batch is retried row by row, like Node, so a rejecting sender gets one
call per row.

## Operations
The outbox table belongs to the producer's database. There is no TTL or cleanup
job. A row the sender keeps rejecting retries forever, with a 15 minute cap,
and needs manual deletion. Every retry delay is jittered to 50 to 100 percent, so a
retry at the cap comes after 7.5 to 15 minutes.

## Differences from the Node library
- A stale "on" flag is treated as on.
- The flag client has no cache bypass argument. Node deletes after an uncached read; here
  a cached off only defers, and a delete needs an off from the remote read.
- Node answers an unknown flag with a rejection. The Python flag client returns a fallback
  or stale answer instead, and the relay treats both as unknown. The write path starts its
  15 second pause only on an error or the 5 second timeout, not on such an answer.
- The write path has no 5 second cache of its own; it reads through the flag client's
  cache on every insert.
- The pool has a 30 second command timeout and a 10 second connect timeout, and an insert
  task is limited to 40 seconds. Node has none of these.
- `stop()` terminates a pool that does not close within 5 seconds, and cancels the running
  round after 5 seconds where Node only stops waiting for it.
- `start()` returns before the first schema check, so `is_ready()` is false right after
  it; Node awaits the first check.
- A failed schema check is logged once per outage as an unreachable database and never as
  a mismatch; Node warns on every failed check.
- The write path awaits a flag read of up to 5 seconds in the background insert task
  before inserting; Node decides synchronously from its own cache, records on unknown and
  refreshes in the background.
- `sslmode=verify` in `DATABASE_URL` is translated to asyncpg's `verify-full`.
- The migration connection has a 60 second command timeout, so a held advisory lock or a
  stuck DDL statement fails the Helm hook instead of waiting forever. Node has none.
- `prepare_rows` rejects a company id that sanitization would change and an event of
  another company; Node sanitizes and does not compare.
- The relay times out a sender call after 30 seconds; Node's publisher has its own 30
  second confirm timeout.
- The relay builds its own flag client when none is injected (see Configuration); Node's
  relay and write path share the host's `isEnabled`.
- There is no `record_in_transaction`.
- The relay's schema check uses the same strict keys as zod, but parses the event id and
  time more leniently: an id without hyphens or a time with a numeric offset such as
  `+00:00` still passes.
- The JSON nesting depth limit is 200 (Node: 500).
- Numbers are sized as Postgres jsonb prints them, because Python reads payloads back with
  `json.loads`: a float with an exponent, such as `1e300`, comes back as a long integer.
  Node does not need this.
- `ActivityCloudEvent.truncated_fields` and the truncation warning use wire paths like
  Node (`actor.id`, `targetName`).
- No broker publisher in this package yet.
