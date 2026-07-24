"""Consumer server (consumer-IdP domain) — reads a producer resource and saves it.

Secured by the **consumer IdP** (the user's home domain). It knows *nothing*
about any specific producer: the caller (host) passes the producer's URL and the
resource URI into the tool call, and the consumer discovers everything else at
runtime.

Run inside Docker Compose (see ``compose/docker-compose.yml``) or locally with
``compose/.env`` loaded (see ``consumer.settings``).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp import Client, FastMCP
from fastmcp.client.auth import BearerAuth
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token
from mcp.types import TextResourceContents
from pydantic import AnyHttpUrl

from mcp_resource_sharing.common.clients import client_settings
from mcp_resource_sharing.common.identity import current_subject
from mcp_resource_sharing.common.logging_setup import configure_logging
from mcp_resource_sharing.common.token_exchange import obtain_producer_token
from mcp_resource_sharing.consumer.settings import consumer_settings

logger = logging.getLogger("rp.consumer")

_verifier = JWTVerifier(
    jwks_uri=str(consumer_settings.idp_jwks_uri),
    issuer=consumer_settings.idp_issuer_value,
    audience=consumer_settings.resource_audience,
)

mcp: FastMCP[Any] = FastMCP("resource-consumer")
# RemoteAuthProvider (not a bare JWTVerifier) so the consumer serves RFC 9728
# protected-resource metadata too — every MCP server MUST advertise its
# authorization server(s), even if this demo never dereferences this one.
mcp.auth = RemoteAuthProvider(
    token_verifier=_verifier,
    authorization_servers=[AnyHttpUrl(consumer_settings.idp_issuer_value)],
    base_url=str(consumer_settings.base_url),
)

DB_PATH = Path(__file__).with_name("archive.db")


def _init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS archived_notes (
                producer    TEXT NOT NULL,
                uri         TEXT NOT NULL,
                owner       TEXT NOT NULL,
                content     TEXT NOT NULL,
                archived_at TEXT NOT NULL,
                PRIMARY KEY (producer, uri)
            )
            """
        )


def _save(producer: str, uri: str, owner: str, content: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO archived_notes "
            "(producer, uri, owner, content, archived_at) VALUES (?, ?, ?, ?, ?)",
            (producer, uri, owner, content, datetime.now(timezone.utc).isoformat()),
        )


@mcp.tool(
    description=(
        "Fetch an MCP resource from a (trusted) producer and save it to the "
        "archive DB. The producer URL and resource URI are supplied by the caller."
    )
)
async def archive_note(producer_url: str, resource_uri: str) -> dict[str, Any]:
    access = get_access_token()
    if access is None:
        raise PermissionError("no authenticated caller")
    user = current_subject()  # verified consumer-IdP user

    if not consumer_settings.is_producer_allowed(producer_url):
        logger.warning(
            "archive_note: DENY untrusted producer_url=%s user=%s", producer_url, user
        )
        # ToolError messages always reach the client, even with error masking on.
        raise ToolError(f"producer not allowed: {producer_url!r}")

    logger.info(
        "archive_note: request producer=%s uri=%s user=%s",
        producer_url,
        resource_uri,
        user,
    )

    producer_token = await obtain_producer_token(
        producer_url, access.token, client_settings.consumer_service_id
    )
    logger.info("archive_note: obtained producer token for user=%s", user)

    async with Client(producer_url, auth=BearerAuth(producer_token)) as producer:
        contents = await producer.read_resource(resource_uri)

    text = "\n".join(
        block.text for block in contents if isinstance(block, TextResourceContents)
    )
    _save(producer=producer_url, uri=resource_uri, owner=user, content=text)
    logger.info(
        "archive_note: saved producer=%s uri=%s user=%s bytes=%d",
        producer_url,
        resource_uri,
        user,
        len(text),
    )
    return {
        "producer": producer_url,
        "uri": resource_uri,
        "archived_by": user,
        "bytes": len(text),
    }


def main() -> None:
    configure_logging()
    _init_db()
    logger.info(
        "consumer listening on :%d (issuer=%s, db=%s, allowed_producers=%s)",
        consumer_settings.port,
        consumer_settings.idp_issuer,
        DB_PATH,
        sorted(consumer_settings.allowed_producer_urls),
    )
    mcp.run(transport="http", port=consumer_settings.port)


if __name__ == "__main__":
    main()
