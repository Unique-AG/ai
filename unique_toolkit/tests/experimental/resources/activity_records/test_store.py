"""Outbox store and migrate entry point against a throwaway Postgres container."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest

asyncpg = pytest.importorskip(
    "asyncpg",
    reason="Activity Records store tests need the activity-records extra",
)

from unique_toolkit.experimental.resources.activity_records import (  # noqa: E402
    migrate as migrate_module,
)
from unique_toolkit.experimental.resources.activity_records.prepare import (  # noqa: E402
    OutboxRow,
    prepare_rows,
)
from unique_toolkit.experimental.resources.activity_records.schemas import (  # noqa: E402
    ActivityActor,
    ActivityCloudEvent,
    ActivityEventData,
)
from unique_toolkit.experimental.resources.activity_records.store import (  # noqa: E402
    _ASYNCPG_DSN_KEYS,
    ACTIVITY_EVENT_OUTBOX_COLUMNS,
    ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL,
    OUTBOX_MAX_BACKOFF_ATTEMPTS,
    OUTBOX_MAX_BACKOFF_SECONDS,
    OUTBOX_STATS_ROW_CAP,
    OutboxStore,
    connect_database,
    create_pool,
    normalize_database_url,
)

from .conftest import docker_container, wait_until  # noqa: E402

pytestmark = pytest.mark.ai

TABLE = '"ActivityEventOutbox"'
STORE_MODULE = "unique_toolkit.experimental.resources.activity_records.store"


@pytest.fixture(scope="module")
def postgres(docker_tests: None) -> Iterator[tuple[str, str]]:
    with docker_container("postgres:17-alpine", 5432, "POSTGRES_PASSWORD=pw") as (
        container,
        port,
    ):
        dsn = f"postgresql://postgres:pw@127.0.0.1:{port}/postgres"
        asyncio.run(wait_until(lambda: asyncpg.connect(dsn), 60))
        yield container, dsn


@pytest.fixture(scope="module")
def database_url(postgres: tuple[str, str]) -> str:
    return postgres[1]


@contextmanager
def _frozen(container: str) -> Iterator[None]:
    subprocess.run(["docker", "pause", container], check=True, capture_output=True)
    try:
        yield
    finally:
        subprocess.run(["docker", "unpause", container], capture_output=True)


@pytest.fixture
async def pool(database_url: str) -> AsyncIterator[asyncpg.Pool]:
    async with asyncpg.create_pool(database_url, min_size=1, max_size=8) as pool:
        await pool.execute(f"DROP TABLE IF EXISTS {TABLE}")
        await pool.execute(ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL)
        yield pool


@pytest.fixture
def store(pool: asyncpg.Pool) -> OutboxStore:
    return OutboxStore(pool)


def _row(index: int = 0, company: str = "c1") -> OutboxRow:
    return OutboxRow(
        id=str(uuid.uuid4()),
        company_id=company,
        source="svc",
        payload={"id": f"event-{index}", "data": {"n": index}},
    )


async def _state(pool: asyncpg.Pool, row_id: str) -> asyncpg.Record | None:
    return await pool.fetchrow(
        f"""SELECT "attempts", "claimToken"::text AS "claimToken", "claimedUntil",
                   "lastError",
                   extract(epoch FROM "nextAttemptAt" - clock_timestamp()) AS "delay"
            FROM {TABLE} WHERE "id" = $1::uuid""",
        row_id,
    )


async def _column_names(pool: asyncpg.Pool) -> set[str]:
    records = await pool.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'ActivityEventOutbox'"
    )
    return {record["column_name"] for record in records}


def test_ddl_is_pinned_to_the_node_constant() -> None:
    assert (
        hashlib.sha256(ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL.encode()).hexdigest()
        == "bcaebb37f31db082735d664e353cfd4290a99acfd932e9af623ddd0ca01e2cea"
    )


def test_normalize_database_url_translates_sslmode_and_connect_timeout() -> None:
    url = "postgresql://user:secret@db/app?sslmode=verify&connect_timeout=3"

    assert normalize_database_url(url) == (
        "postgresql://user:secret@db/app?sslmode=verify-full",
        3,
    )


@pytest.mark.parametrize("value", ["0", "-5"])
def test_a_non_positive_connect_timeout_means_the_default(value: str) -> None:
    url = f"postgresql://u:p@db/app?connect_timeout={value}"

    assert normalize_database_url(url) == ("postgresql://u:p@db/app", None)


def test_normalize_database_url_keeps_what_asyncpg_reads() -> None:
    url = (
        "postgresql://u:p@db:5432/app?sslrootcert=/ca.pem&target_session_attrs=primary"
    )

    dsn, timeout = normalize_database_url(url)

    assert timeout is None
    assert asyncpg_server_settings(dsn) == {}
    assert "sslrootcert=%2Fca.pem" in dsn and "target_session_attrs=primary" in dsn


def test_normalize_database_url_keeps_application_name_and_still_drops_the_rest(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "unique_toolkit.experimental.resources.activity_records.store._logged_dropped_keys",
        set(),
    )
    url = "postgresql://u:p@db/app?application_name=outbox-test&schema=public"

    dsn, _ = normalize_database_url(url)
    normalize_database_url(url)

    assert dsn == "postgresql://u:p@db/app?application_name=outbox-test"
    messages = [r.getMessage() for r in caplog.records]
    assert len(messages) == 1
    assert "schema" in messages[0] and "application_name" not in messages[0]


def asyncpg_server_settings(dsn: str) -> dict[str, str]:
    """What asyncpg would send to the server as settings for this DSN (no database needed)."""
    parser = asyncpg.connect_utils._parse_connect_dsn_and_args  # type: ignore[attr-defined]
    arguments = dict.fromkeys(inspect.signature(parser).parameters)
    _, params = parser(**{**arguments, "dsn": dsn})
    return params.server_settings or {}


_VALID_VALUES = {
    "sslmode": "disable",
    "sslnegotiation": "postgres",
    "ssl_min_protocol_version": "TLSv1.2",
    "ssl_max_protocol_version": "TLSv1.3",
    "target_session_attrs": "any",
    "gsslib": "gssapi",
}


@pytest.mark.parametrize("key", sorted(_ASYNCPG_DSN_KEYS - {"application_name"}))
def test_every_allowed_dsn_key_is_read_by_the_installed_asyncpg(key: str) -> None:
    value = _VALID_VALUES.get(key, "x")
    dsn = f"postgresql://u:p@db/app?sslmode=disable&{key}={value}"

    assert key not in asyncpg_server_settings(dsn)


def test_normalize_database_url_drops_service_that_asyncpg_0_30_sends_to_the_server() -> (
    None
):
    dsn, _ = normalize_database_url("postgresql://u:p@db/app?service=outbox")

    assert dsn == "postgresql://u:p@db/app"


def test_asyncpg_sends_unsupported_parameters_to_the_server_and_we_drop_them() -> None:
    url = (
        "postgresql://u:p@db/app?connect_timeout=3&schema=public"
        "&connection_limit=5&sslaccept=strict"
    )

    assert set(asyncpg_server_settings(url)) == {
        "connect_timeout",
        "schema",
        "connection_limit",
        "sslaccept",
    }
    dsn, timeout = normalize_database_url(url)
    assert asyncpg_server_settings(dsn) == {}
    assert timeout == 3


def test_normalize_database_url_logs_only_the_names_of_dropped_parameters_once(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "unique_toolkit.experimental.resources.activity_records.store._logged_dropped_keys",
        set(),
    )
    url = "postgresql://u:p@db/app?schema=SECRET-SCHEMA&connection_limit=SECRET-LIMIT"

    normalize_database_url(url)
    normalize_database_url(url)

    messages = [r.getMessage() for r in caplog.records]
    assert len(messages) == 1
    assert "connection_limit" in messages[0] and "schema" in messages[0]
    assert "SECRET" not in caplog.text


class TestMigrate:
    async def test_main_as_subprocess(
        self, database_url: str, pool: asyncpg.Pool
    ) -> None:
        await pool.execute(f"DROP TABLE {TABLE}")
        command = [
            sys.executable,
            "-m",
            "unique_toolkit.experimental.resources.activity_records.migrate",
        ]
        env = {**os.environ, "DATABASE_URL": database_url}

        first = subprocess.run(command, env=env, capture_output=True, text=True)
        second = subprocess.run(command, env=env, capture_output=True, text=True)

        assert (first.returncode, second.returncode) == (0, 0)
        assert "created" in first.stdout
        assert "already exists" in second.stdout
        assert await OutboxStore(pool).has_expected_columns()
        columns = {
            r["column_name"]: r["data_type"]
            for r in await pool.fetch(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'ActivityEventOutbox'"
            )
        }
        assert columns == ACTIVITY_EVENT_OUTBOX_COLUMNS
        indexes = {
            r["indexname"]
            for r in await pool.fetch(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'ActivityEventOutbox'"
            )
        }
        assert indexes == {
            "ActivityEventOutbox_pkey",
            "ActivityEventOutbox_nextAttemptAt_idx",
            "ActivityEventOutbox_createdAt_idx",
        }

    async def test_concurrent_runs_create_the_table_once(
        self, database_url: str, pool: asyncpg.Pool
    ) -> None:
        await pool.execute(f"DROP TABLE {TABLE}")

        results = await asyncio.gather(
            *(migrate_module.migrate(database_url) for _ in range(4))
        )

        assert results.count(True) == 1
        assert await OutboxStore(pool).has_expected_columns()

    async def test_a_held_advisory_lock_fails_the_migration_instead_of_hanging(
        self,
        database_url: str,
        pool: asyncpg.Pool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(migrate_module, "MIGRATION_COMMAND_TIMEOUT_SECONDS", 0.5)
        async with pool.acquire() as holder:
            await holder.execute(
                "SELECT pg_advisory_lock(hashtext('ActivityEventOutbox'))"
            )
            try:
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(migrate_module.migrate(database_url), 10)
            finally:
                await holder.execute(
                    "SELECT pg_advisory_unlock(hashtext('ActivityEventOutbox'))"
                )

    async def test_a_server_that_freezes_mid_migration_fails_within_the_timeout(
        self,
        postgres: tuple[str, str],
        pool: asyncpg.Pool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        container, database_url = postgres
        connect = migrate_module.connect_database

        async def connect_then_freeze(*args, **kwargs):
            connection = await connect(*args, **kwargs)
            subprocess.run(["docker", "pause", container], check=True)
            return connection

        monkeypatch.setattr(migrate_module, "MIGRATION_COMMAND_TIMEOUT_SECONDS", 0.5)
        monkeypatch.setattr(migrate_module, "connect_database", connect_then_freeze)
        try:
            started = asyncio.get_running_loop().time()
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(migrate_module.migrate(database_url), 10)
            assert asyncio.get_running_loop().time() - started < 5
        finally:
            subprocess.run(["docker", "unpause", container], capture_output=True)

    async def test_a_table_with_a_missing_column_fails_the_migration(
        self, database_url: str, pool: asyncpg.Pool
    ) -> None:
        await pool.execute(f'ALTER TABLE {TABLE} DROP COLUMN "lastError"')

        with pytest.raises(migrate_module.OutboxTableMismatch):
            await migrate_module.migrate(database_url)

        assert "lastError" not in await _column_names(pool)

    async def test_a_table_with_a_wrong_column_type_fails_the_migration(
        self, database_url: str, pool: asyncpg.Pool
    ) -> None:
        await pool.execute(
            f'ALTER TABLE {TABLE} ALTER COLUMN "claimToken" TYPE text USING "claimToken"::text'
        )

        with pytest.raises(migrate_module.OutboxTableMismatch):
            await migrate_module.migrate(database_url)

    async def test_main_exits_non_zero_with_a_clear_message_on_a_mismatched_table(
        self, database_url: str, pool: asyncpg.Pool
    ) -> None:
        await pool.execute(f'ALTER TABLE {TABLE} DROP COLUMN "lastError"')
        command = [
            sys.executable,
            "-m",
            "unique_toolkit.experimental.resources.activity_records.migrate",
        ]

        result = subprocess.run(
            command,
            env={**os.environ, "DATABASE_URL": database_url},
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "ActivityEventOutbox" in result.stderr
        assert "column is missing or has a wrong type" in result.stderr
        assert database_url not in result.stderr

    async def test_an_extra_column_is_allowed(
        self, database_url: str, pool: asyncpg.Pool
    ) -> None:
        await pool.execute(f'ALTER TABLE {TABLE} ADD COLUMN "extra" TEXT')

        assert await migrate_module.migrate(database_url) is False
        assert "extra" in await _column_names(pool)

    def test_failure_exits_non_zero_without_echoing_the_url(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:TOPSECRET@127.0.0.1:1/db")

        assert migrate_module.main() == 1
        captured = capsys.readouterr()
        assert "TOPSECRET" not in captured.out + captured.err
        assert "127.0.0.1" not in captured.out + captured.err

    def test_missing_database_url_exits_non_zero(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)

        assert migrate_module.main() == 1
        assert "DATABASE_URL" in capsys.readouterr().err


class TestColumnCheck:
    async def test_passes_on_the_migrated_table(self, store: OutboxStore) -> None:
        assert await store.has_expected_columns()

    async def test_fails_when_a_column_is_missing(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        await pool.execute(f'ALTER TABLE {TABLE} DROP COLUMN "lastError"')
        assert not await store.has_expected_columns()

    async def test_fails_when_a_column_has_the_wrong_type(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        await pool.execute(
            f'ALTER TABLE {TABLE} ALTER COLUMN "claimToken" TYPE text USING "claimToken"::text'
        )
        assert not await store.has_expected_columns()

    async def test_passes_with_an_extra_column(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        await pool.execute(f'ALTER TABLE {TABLE} ADD COLUMN "extra" TEXT')
        assert await store.has_expected_columns()


class TestInsert:
    async def test_dedupes_by_id(self, store: OutboxStore, pool: asyncpg.Pool) -> None:
        row = _row()

        first = await store.insert([row, row])
        second = await store.insert([row])

        assert (first, second) == (1, 0)
        assert await pool.fetchval(f"SELECT count(*) FROM {TABLE}") == 1

    async def test_inserts_many_rows_and_keeps_the_payload(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        rows = [_row(i, company=f"c{i % 3}") for i in range(500)]

        assert await store.insert(rows) == 500

        stored = await pool.fetchrow(
            f'SELECT "companyId", "source", "payload"::text AS payload FROM {TABLE} '
            'WHERE "id" = $1::uuid',
            rows[7].id,
        )
        assert stored is not None
        assert (stored["companyId"], stored["source"]) == ("c1", "svc")
        assert '"event-7"' in stored["payload"]

    async def test_inserts_prepared_non_finite_values_as_null(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        event = ActivityCloudEvent(
            source="svc",
            type="activity.test",
            time=datetime.now(UTC),
            data=ActivityEventData(
                actor=ActivityActor(id="user", type="user"),
                company_id="c1",
                critical_data={
                    "nan": float("nan"),
                    "infinity": float("inf"),
                    "nested": [float("-inf")],
                },
            ),
        )
        (row,) = prepare_rows("c1", [event]).rows

        assert await store.insert([row]) == 1
        stored = await pool.fetchval(
            f'SELECT "payload"::text FROM {TABLE} WHERE "id" = $1::uuid', row.id
        )
        assert stored is not None
        payload = json.loads(stored)
        assert payload["data"]["criticalData"] == {
            "nan": None,
            "infinity": None,
            "nested": [None],
        }

    async def test_inserts_nothing_for_no_rows(self, store: OutboxStore) -> None:
        assert await store.insert([]) == 0


class TestClaim:
    async def test_returns_up_to_the_limit(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        rows = [_row(i) for i in range(30)]
        rows[0] = OutboxRow(
            rows[0].id,
            "café",
            "svc",
            {"id": rows[0].id, "data": {"text": "café", "nested": [1, "二"]}},
        )
        await store.insert(rows)
        await pool.execute(
            f"""UPDATE {TABLE} SET "nextAttemptAt" = now() - interval '1 hour'
                WHERE "id" = $1::uuid""",
            rows[0].id,
        )

        token = str(uuid.uuid4())
        claimed = await store.claim(token, 10, 90)

        got = {c.id: (c.company_id, c.source, c.payload) for c in claimed}
        expected = {r.id: (r.company_id, r.source, r.payload) for r in rows}
        assert len(claimed) == len(got) == 10
        assert rows[0].id in got
        assert got.items() <= expected.items()
        lease_seconds = await pool.fetchval(
            f"""SELECT extract(epoch FROM "claimedUntil" - now())
                FROM {TABLE} WHERE "claimToken" = $1::uuid""",
            token,
        )
        assert lease_seconds is not None
        assert 89 <= lease_seconds <= 90

    async def test_skips_rows_not_yet_due(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        due, later = _row(1), _row(2)
        await store.insert([due, later])
        await pool.execute(
            f"UPDATE {TABLE} SET \"nextAttemptAt\" = now() + interval '1 hour' "
            'WHERE "id" = $1::uuid',
            later.id,
        )

        claimed = await store.claim(str(uuid.uuid4()), 100, 90)

        assert [c.id for c in claimed] == [due.id]

    async def test_skips_rows_under_a_live_lease_and_reclaims_after_expiry(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        row = _row()
        await store.insert([row])
        assert len(await store.claim(str(uuid.uuid4()), 100, 90)) == 1

        assert await store.claim(str(uuid.uuid4()), 100, 90) == []

        await pool.execute(
            f"UPDATE {TABLE} SET \"claimedUntil\" = now() - interval '1 second'"
        )
        reclaimed = await store.claim(str(uuid.uuid4()), 100, 90)
        assert [c.id for c in reclaimed] == [row.id]

    async def test_concurrent_claimers_get_disjoint_sets(
        self, pool: asyncpg.Pool
    ) -> None:
        stores = [OutboxStore(pool) for _ in range(4)]
        await stores[0].insert([_row(i) for i in range(200)])

        results = await asyncio.gather(
            *(s.claim(str(uuid.uuid4()), 100, 90) for s in stores)
        )

        ids = [c.id for claimed in results for c in claimed]
        assert len(ids) == len(set(ids)) == 200

    async def test_skips_rows_locked_by_another_transaction(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        locked, free = _row(1), _row(2)
        await store.insert([locked, free])

        async with pool.acquire() as connection, connection.transaction():
            await connection.execute(
                f'SELECT 1 FROM {TABLE} WHERE "id" = $1::uuid FOR UPDATE', locked.id
            )
            claimed = await asyncio.wait_for(
                store.claim(str(uuid.uuid4()), 100, 90),
                5,
            )

        assert [c.id for c in claimed] == [free.id]


class TestFencedWrites:
    async def test_stale_token_changes_nothing(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        rows = [_row(1), _row(2)]
        ids = [r.id for r in rows]
        await store.insert(rows)
        token = str(uuid.uuid4())
        await store.claim(token, 100, 90)
        stale = str(uuid.uuid4())

        assert await store.delete_claimed(stale, ids) == []
        assert await store.reschedule_with_backoff(stale, ids, "X") == []
        assert await store.defer(stale, ids, 60) == 0

        for row_id in ids:
            state = await _state(pool, row_id)
            assert state is not None
            assert state["claimToken"] == token
            assert state["attempts"] == 0
            assert state["lastError"] is None

    async def test_delete_removes_only_the_requested_claimed_rows(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        rows = [_row(i) for i in range(3)]
        await store.insert(rows)
        token = str(uuid.uuid4())
        await store.claim(token, 100, 90)

        deleted = await store.delete_claimed(token, [rows[0].id, rows[1].id])

        assert sorted(deleted) == sorted([rows[0].id, rows[1].id])
        assert await pool.fetchval(f"SELECT count(*) FROM {TABLE}") == 1

    @pytest.mark.parametrize("attempts", [0, 1, 5, 11, 25, 1024, 100_000])
    async def test_backoff_counts_the_attempt_and_delays_within_the_formula(
        self, store: OutboxStore, pool: asyncpg.Pool, attempts: int
    ) -> None:
        row = _row()
        await store.insert([row])
        await pool.execute(f'UPDATE {TABLE} SET "attempts" = {attempts}')
        token = str(uuid.uuid4())
        await store.claim(token, 100, 90)

        result = await store.reschedule_with_backoff(token, [row.id], "TimeoutError")

        assert result == [attempts + 1]
        state = await _state(pool, row.id)
        assert state is not None
        assert state["attempts"] == attempts + 1
        assert state["lastError"] == "TimeoutError"
        assert state["claimToken"] is None and state["claimedUntil"] is None
        base = min(2 ** min(attempts, 20), 900)
        assert 0.5 * base - 1 <= state["delay"] <= base

    async def test_defer_keeps_the_attempt_count_and_jitters_the_delay(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        row = _row()
        await store.insert([row])
        token = str(uuid.uuid4())
        await store.claim(token, 100, 90)

        assert await store.defer(token, [row.id], 100) == 1

        state = await _state(pool, row.id)
        assert state is not None
        assert state["attempts"] == 0
        assert state["claimToken"] is None and state["claimedUntil"] is None
        assert 49 <= state["delay"] <= 100

    async def test_defer_with_zero_hands_back_immediately(
        self, store: OutboxStore
    ) -> None:
        row = _row()
        await store.insert([row])
        token = str(uuid.uuid4())
        await store.claim(token, 100, 90)

        await store.defer(token, [row.id], 0)

        assert [c.id for c in await store.claim(str(uuid.uuid4()), 100, 90)] == [row.id]


class TestStats:
    async def test_empty_table(self, store: OutboxStore) -> None:
        stats = await store.stats()

        assert (stats.pending_rows, stats.oldest_pending_age_seconds) == (0, 0.0)
        assert stats.rows_at_max_backoff == 0

    async def test_counts_pending_rows_age_and_rows_at_max_backoff(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        rows = [_row(i) for i in range(4)]
        await store.insert(rows)
        await pool.execute(
            f'UPDATE {TABLE} SET "attempts" = $1 WHERE "id" = ANY($2::uuid[])',
            11,
            [rows[0].id, rows[1].id],
        )
        await pool.execute(
            f'UPDATE {TABLE} SET "attempts" = $1 WHERE "id" = $2::uuid',
            10,
            rows[2].id,
        )
        await pool.execute(
            f"UPDATE {TABLE} SET \"createdAt\" = now() - interval '1 hour' "
            'WHERE "id" = $1::uuid',
            rows[3].id,
        )

        stats = await store.stats()

        assert stats.pending_rows == 4
        assert stats.rows_at_max_backoff == 2
        assert 3599 <= stats.oldest_pending_age_seconds <= 3700

    def test_alert_parity_constants_are_frozen(self) -> None:
        assert OUTBOX_MAX_BACKOFF_SECONDS == 900
        assert OUTBOX_MAX_BACKOFF_ATTEMPTS == 11
        assert OUTBOX_STATS_ROW_CAP == 100_000

    async def test_row_counts_are_capped(
        self, store: OutboxStore, pool: asyncpg.Pool
    ) -> None:
        extra = 5
        await pool.execute(
            f"""INSERT INTO {TABLE} ("id", "companyId", "source", "payload")
                SELECT gen_random_uuid(), 'c', 's', '{{}}'::jsonb
                FROM generate_series(1, $1::int)""",
            100_000 + extra,
        )

        stats = await store.stats()

        assert stats.pending_rows == 100_000


class TestConnectionFromUrl:
    async def test_application_name_in_the_url_reaches_the_server(
        self, database_url: str
    ) -> None:
        connection = await connect_database(
            f"{database_url}?application_name=outbox-test&schema=public"
        )
        try:
            assert await connection.fetchval("SHOW application_name") == "outbox-test"
        finally:
            await connection.close()


class TestPoolTimeouts:
    async def test_a_server_that_never_answers_fails_at_the_connect_timeout(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(STORE_MODULE + ".POOL_CONNECT_TIMEOUT_SECONDS", 1)
        server = await asyncio.start_server(lambda _r, _w: None, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            started = asyncio.get_running_loop().time()
            with pytest.raises(TimeoutError):
                await create_pool(
                    f"postgresql://u:p@127.0.0.1:{port}/db",
                    min_size=1,
                    max_size=1,
                )
            assert asyncio.get_running_loop().time() - started < 5
        finally:
            server.close()

    async def test_a_query_slower_than_the_command_timeout_raises(
        self, database_url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(STORE_MODULE + ".POOL_COMMAND_TIMEOUT_SECONDS", 1)
        slow_pool = await create_pool(database_url, min_size=1, max_size=1)
        try:
            started = asyncio.get_running_loop().time()
            with pytest.raises(TimeoutError):
                await slow_pool.execute("SELECT pg_sleep(10)")
            assert asyncio.get_running_loop().time() - started < 5
        finally:
            slow_pool.terminate()

    async def test_a_frozen_server_fails_a_store_call_within_the_timeout(
        self, postgres: tuple[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        container, database_url = postgres
        monkeypatch.setattr(STORE_MODULE + ".POOL_COMMAND_TIMEOUT_SECONDS", 1)
        frozen_pool = await create_pool(database_url, min_size=1, max_size=1)
        try:
            with _frozen(container):
                started = asyncio.get_running_loop().time()
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(OutboxStore(frozen_pool).stats(), 10)
                assert asyncio.get_running_loop().time() - started < 5
        finally:
            frozen_pool.terminate()
