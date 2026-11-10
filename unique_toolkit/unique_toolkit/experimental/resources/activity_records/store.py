"""Run all SQL for the Activity Records outbox with fixed names and bind parameters."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from unique_toolkit.experimental.resources.activity_records.config import (
    ACTIVITY_RECORDS_INSTALL_HINT,
    OUTBOX_MAX_BACKOFF_ATTEMPTS,
)
from unique_toolkit.experimental.resources.activity_records.json_size import json_bytes
from unique_toolkit.experimental.resources.activity_records.prepare import (
    OutboxRow,
)

try:
    import asyncpg  # pyright: ignore[reportMissingImports]
except ImportError as error:  # pragma: no cover
    raise ImportError(
        f"The Activity Records outbox needs asyncpg. {ACTIVITY_RECORDS_INSTALL_HINT}"
    ) from error


logger = logging.getLogger(__name__)

# The DSN parameters that asyncpg 0.30 (the declared minimum) and newer versions both read, plus
# application_name, a real server setting. Any other key goes to the server, which rejects it.
_ASYNCPG_DSN_KEYS: Final = frozenset(
    {
        "host",
        "port",
        "user",
        "password",
        "dbname",
        "database",
        "passfile",
        "sslmode",
        "sslcert",
        "sslkey",
        "sslrootcert",
        "sslnegotiation",
        "sslcrl",
        "sslpassword",
        "ssl_min_protocol_version",
        "ssl_max_protocol_version",
        "target_session_attrs",
        "krbsrvname",
        "gsslib",
        "application_name",
    }
)
_logged_dropped_keys: set[str] = set()


def normalize_database_url(database_url: str) -> tuple[str, int | None]:
    """Return the DSN asyncpg can parse and the connect timeout from ``connect_timeout``.

    ``sslmode=verify`` (the chart's value) becomes ``verify-full``. Parameters asyncpg does not
    read are dropped, and only their names are logged, once."""
    parts = urlsplit(database_url)
    kept: list[tuple[str, str]] = []
    dropped: list[str] = []
    timeout: int | None = None
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key == "connect_timeout":
            try:
                timeout = int(value)
            except ValueError:
                dropped.append(key)
        elif key not in _ASYNCPG_DSN_KEYS:
            dropped.append(key)
        elif key == "sslmode" and value == "verify":
            kept.append((key, "verify-full"))
        else:
            kept.append((key, value))
    new_names = sorted(set(dropped) - _logged_dropped_keys)
    if new_names:
        _logged_dropped_keys.update(new_names)
        logger.warning(
            "Ignoring DATABASE_URL parameters that asyncpg does not support: %s",
            ", ".join(new_names),
        )
    dsn = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment)
    )
    # PostgreSQL reads 0 as no timeout, but asyncpg reads it as an immediate deadline.
    return dsn, timeout if timeout is not None and timeout > 0 else None


async def connect_database(
    database_url: str, *, command_timeout: float | None = None
) -> asyncpg.Connection:
    dsn, timeout = normalize_database_url(database_url)
    if timeout is None:
        return await asyncpg.connect(dsn, command_timeout=command_timeout)
    return await asyncpg.connect(dsn, timeout=timeout, command_timeout=command_timeout)


# Without these a frozen database holds a query forever and a new connection waits 60 s.
POOL_COMMAND_TIMEOUT_SECONDS: Final = 30.0
POOL_CONNECT_TIMEOUT_SECONDS: Final = 10.0


async def create_pool(
    database_url: str, *, min_size: int, max_size: int
) -> asyncpg.Pool:
    dsn, dsn_timeout = normalize_database_url(database_url)
    return await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=POOL_COMMAND_TIMEOUT_SECONDS,
        timeout=dsn_timeout or POOL_CONNECT_TIMEOUT_SECONDS,
    )


# Copied into the producing service's migration; keep it byte for byte equal to the Node constant.
ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL: Final = """-- CreateTable
CREATE TABLE "ActivityEventOutbox" (
    "id" UUID NOT NULL,
    "companyId" TEXT NOT NULL,
    "source" TEXT NOT NULL,
    "payload" JSONB NOT NULL,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "attempts" INTEGER NOT NULL DEFAULT 0,
    "nextAttemptAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "claimedUntil" TIMESTAMPTZ(6),
    "claimToken" UUID,
    "lastError" TEXT,

    CONSTRAINT "ActivityEventOutbox_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "ActivityEventOutbox_nextAttemptAt_idx" ON "ActivityEventOutbox"("nextAttemptAt");

-- CreateIndex
CREATE INDEX "ActivityEventOutbox_createdAt_idx" ON "ActivityEventOutbox"("createdAt");
"""

# Column name to ``information_schema.columns.data_type``; extra columns are allowed.
ACTIVITY_EVENT_OUTBOX_COLUMNS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "id": "uuid",
        "companyId": "text",
        "source": "text",
        "payload": "jsonb",
        "createdAt": "timestamp with time zone",
        "attempts": "integer",
        "nextAttemptAt": "timestamp with time zone",
        "claimedUntil": "timestamp with time zone",
        "claimToken": "uuid",
        "lastError": "text",
    }
)

# Delay after a failed publish is min(2^attempts, cap) seconds, jittered to 50-100 %.
OUTBOX_MAX_BACKOFF_SECONDS: Final = 15 * 60
# power(2, ...) overflows double precision past 2^1023, and a row retries forever.
_BACKOFF_EXPONENT_CEILING: Final = 20
# The row-count gauges read at most this many rows so a large backlog stays cheap.
OUTBOX_STATS_ROW_CAP: Final = 100_000


@dataclass(frozen=True, slots=True)
class ClaimedOutboxRow(OutboxRow):
    attempts: int


@dataclass(frozen=True, slots=True)
class OutboxStats:
    pending_rows: int
    oldest_pending_age_seconds: float
    rows_at_max_backoff: int


def _affected(status: str) -> int:
    return int(status.rsplit(" ", 1)[-1])


async def outbox_columns_match(executor: asyncpg.Pool | asyncpg.Connection) -> bool:
    """True when every column in ``ACTIVITY_EVENT_OUTBOX_COLUMNS`` exists with its type in
    ``current_schema()``. Extra columns are allowed."""
    records = await executor.fetch(
        """
        SELECT column_name AS "name", data_type AS "type"
        FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = 'ActivityEventOutbox'"""
    )
    actual = {record["name"]: record["type"] for record in records}
    return all(
        actual.get(name) == type_
        for name, type_ in ACTIVITY_EVENT_OUTBOX_COLUMNS.items()
    )


class OutboxStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    def _connection(self) -> asyncpg.pool.PoolAcquireContext:
        # The acquire timeout also bounds release, which pool.execute() leaves unbounded.
        return self._pool.acquire(timeout=POOL_COMMAND_TIMEOUT_SECONDS)

    async def insert(self, rows: Sequence[OutboxRow]) -> int:
        wire = [
            {
                "id": row.id,
                "companyId": row.company_id,
                "source": row.source,
                "payload": row.payload,
            }
            for row in rows
        ]
        async with self._connection() as connection:
            status = await connection.execute(
                """
                INSERT INTO "ActivityEventOutbox" ("id", "companyId", "source", "payload")
                SELECT r."id", r."companyId", r."source", r."payload"
                FROM jsonb_to_recordset($1::jsonb)
                  AS r("id" uuid, "companyId" text, "source" text, "payload" jsonb)
                ON CONFLICT ("id") DO NOTHING""",
                json_bytes(wire).decode("utf-8"),
            )
        return _affected(status)

    async def claim(
        self, claim_token: str, limit: int, lease_seconds: int
    ) -> list[ClaimedOutboxRow]:
        """Claims due rows for ``lease_seconds``. The UPDATE commits on its own, so no lock is
        held while publishing."""
        async with self._connection() as connection:
            records = await connection.fetch(
                """
                UPDATE "ActivityEventOutbox"
                SET "claimToken" = $1::uuid,
                    "claimedUntil" = now() + $2::int * interval '1 second'
                WHERE "id" IN (
                  SELECT "id" FROM "ActivityEventOutbox"
                  WHERE "nextAttemptAt" <= now()
                    AND ("claimedUntil" IS NULL OR "claimedUntil" < now())
                  ORDER BY "nextAttemptAt"
                  LIMIT $3::int
                  FOR UPDATE SKIP LOCKED
                )
                RETURNING "id"::text AS "id", "companyId", "source", "payload", "attempts"
                """,
                claim_token,
                lease_seconds,
                limit,
            )
        return [
            ClaimedOutboxRow(
                id=record["id"],
                company_id=record["companyId"],
                source=record["source"],
                payload=json.loads(record["payload"]),
                attempts=record["attempts"],
            )
            for record in records
        ]

    async def delete_claimed(self, claim_token: str, ids: Sequence[str]) -> list[str]:
        """Fenced by ``claim_token``: a relay whose lease expired and was re-claimed deletes
        nothing. Returns the ids it deleted."""
        async with self._connection() as connection:
            records = await connection.fetch(
                """
                DELETE FROM "ActivityEventOutbox"
                WHERE "claimToken" = $1::uuid AND "id" = ANY($2::uuid[])
                RETURNING "id"::text AS "id"
                """,
                claim_token,
                list(ids),
            )
        return [record["id"] for record in records]

    async def reschedule_with_backoff(
        self, claim_token: str, ids: Sequence[str], last_error: str
    ) -> list[int]:
        """Counts an attempt and backs off. Returns each rescheduled row's new attempt count."""
        async with self._connection() as connection:
            records = await connection.fetch(
                """
                UPDATE "ActivityEventOutbox"
                SET "attempts" = "attempts" + 1,
                    "nextAttemptAt" = now()
                      + least(power(2, least("attempts", $4::int)), $5::int)
                      * (0.5 + random() * 0.5) * interval '1 second',
                    "claimedUntil" = NULL,
                    "claimToken" = NULL,
                    "lastError" = $3
                WHERE "claimToken" = $1::uuid AND "id" = ANY($2::uuid[])
                RETURNING "attempts"
                """,
                claim_token,
                list(ids),
                last_error,
                _BACKOFF_EXPONENT_CEILING,
                OUTBOX_MAX_BACKOFF_SECONDS,
            )
        return [record["attempts"] for record in records]

    async def defer(
        self, claim_token: str, ids: Sequence[str], delay_seconds: int
    ) -> int:
        """Releases rows for a later try without counting an attempt, jittered to 50-100 % of
        the delay so rows deferred together do not all come due together."""
        async with self._connection() as connection:
            status = await connection.execute(
                """
                UPDATE "ActivityEventOutbox"
                SET "nextAttemptAt" = now() + $3::int * (0.5 + random() * 0.5) * interval '1 second',
                    "claimedUntil" = NULL,
                    "claimToken" = NULL
                WHERE "claimToken" = $1::uuid AND "id" = ANY($2::uuid[])""",
                claim_token,
                list(ids),
                delay_seconds,
            )
        return _affected(status)

    async def stats(self) -> OutboxStats:
        """Row counts are capped at ``OUTBOX_STATS_ROW_CAP``; the oldest age reads the
        ``createdAt`` index."""
        async with self._connection() as connection:
            record = await connection.fetchrow(
                """
                WITH sample AS (SELECT "attempts" FROM "ActivityEventOutbox" LIMIT $1::int)
                SELECT (SELECT count(*) FROM sample)::int AS "pendingRows",
                       coalesce(extract(epoch FROM now() - (SELECT min("createdAt") FROM "ActivityEventOutbox")), 0)::float8
                         AS "oldestPendingAgeSeconds",
                       (SELECT count(*) FROM sample WHERE "attempts" >= $2::int)::int
                         AS "rowsAtMaxBackoff"
                """,
                OUTBOX_STATS_ROW_CAP,
                OUTBOX_MAX_BACKOFF_ATTEMPTS,
            )
        assert record is not None
        return OutboxStats(
            pending_rows=record["pendingRows"],
            oldest_pending_age_seconds=record["oldestPendingAgeSeconds"],
            rows_at_max_backoff=record["rowsAtMaxBackoff"],
        )

    async def has_expected_columns(self) -> bool:
        async with self._connection() as connection:
            return await outbox_columns_match(connection)
