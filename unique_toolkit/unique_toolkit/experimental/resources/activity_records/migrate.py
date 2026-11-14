"""Create the Activity Records outbox table from ``DATABASE_URL``."""

from __future__ import annotations

import asyncio
import os
import sys

from unique_toolkit.experimental.resources.activity_records.store import (
    ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL,
    connect_database,
    outbox_columns_match,
)

# Without a deadline, waiting for the advisory lock or running DDL can hang a Helm hook forever.
MIGRATION_COMMAND_TIMEOUT_SECONDS = 60.0


class OutboxTableMismatch(Exception):
    """The table exists but a column is missing or has a wrong type."""


async def migrate(database_url: str) -> bool:
    """Returns True when the table was created, False when it already existed.

    Raises ``OutboxTableMismatch`` when the table does not have the expected columns."""
    connection = await connect_database(
        database_url, command_timeout=MIGRATION_COMMAND_TIMEOUT_SECONDS
    )
    try:
        await connection.execute("BEGIN")
        await connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext('ActivityEventOutbox'))"
        )
        created = not await connection.fetchval(
            """SELECT to_regclass(
                format('%I."ActivityEventOutbox"', current_schema())
            ) IS NOT NULL"""
        )
        if created:
            await connection.execute(ACTIVITY_EVENT_OUTBOX_INITIAL_MIGRATION_SQL)
        if not await outbox_columns_match(connection):
            raise OutboxTableMismatch
        await connection.execute("COMMIT")
        return created
    except TimeoutError:
        # asyncpg 0.30 queues ROLLBACK and close behind a cancel request a frozen server never answers.
        connection.terminate()
        raise
    finally:
        # Closing without COMMIT rolls the transaction back on the server.
        await connection.close(timeout=MIGRATION_COMMAND_TIMEOUT_SECONDS)


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1
    try:
        created = asyncio.run(migrate(database_url))
    except OutboxTableMismatch:
        print(
            "The ActivityEventOutbox table exists but a column is missing or has a "
            "wrong type; fix the table before the service starts",
            file=sys.stderr,
        )
        return 1
    except Exception as error:
        # The message can echo the connection string, so print the class name only.
        print(
            f"Activity Records migration failed: {type(error).__name__}",
            file=sys.stderr,
        )
        return 1
    print(
        "ActivityEventOutbox created"
        if created
        else "ActivityEventOutbox already exists"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
