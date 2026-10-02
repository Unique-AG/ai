"""Producer server (producer-IdP domain) — creates owned resources and exposes them.

Secured by the **producer IdP** (Keycloak): every request must carry a valid
producer-IdP JWT (so the caller has been through token exchange). The owner of
a note is taken from the *verified* token `sub`, never from `_meta`.

Run inside Docker Compose (see ``compose/docker-compose.yml``) or locally with
``compose/.env`` loaded (see ``producer.settings``).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl

from mcp_resource_sharing.common.identity import current_subject
from mcp_resource_sharing.common.logging_setup import configure_logging
from mcp_resource_sharing.producer.settings import producer_settings

logger = logging.getLogger("rp.producer")

_verifier = JWTVerifier(
    jwks_uri=str(producer_settings.idp_jwks_uri),
    issuer=str(producer_settings.idp_issuer),
    audience=producer_settings.resource_audience,
)

mcp: FastMCP[Any] = FastMCP("resource-producer")
mcp.auth = RemoteAuthProvider(
    token_verifier=_verifier,
    authorization_servers=[AnyHttpUrl(str(producer_settings.idp_issuer))],
    base_url=str(producer_settings.base_url),
)

_NOTES: dict[str, dict[str, str]] = {}


@mcp.tool(
    description="Create a note owned by the verified caller and return its resource URI."
)
async def create_note(title: str, body: str) -> dict[str, str]:
    owner = current_subject()
    note_id = uuid.uuid4().hex[:8]
    _NOTES[note_id] = {
        "owner": owner,
        "title": title,
        "content": f"# {title}\n\n{body}\n",
    }
    logger.info("create_note: note://%s created, owner=%s", note_id, owner)
    return {"uri": f"note://{note_id}", "owner": owner}


@mcp.resource("note://{note_id}")
def read_note(note_id: str) -> str:
    """Read a note's content — only the owner is allowed."""
    note = _NOTES.get(note_id)
    if note is None:
        logger.warning("read_note: note://%s not found", note_id)
        # ResourceError messages always reach the client, even when FastMCP's
        # mask_error_details is on — the right channel for *intentional* errors.
        raise ResourceError(f"note {note_id!r} not found")

    requester = current_subject()
    if requester != note["owner"]:
        logger.warning(
            "read_note: DENY note://%s requester=%s owner=%s",
            note_id,
            requester,
            note["owner"],
        )
        # Deliberately does not reveal *who* owns the note.
        raise ResourceError(
            f"access denied: user {requester!r} is not the owner of note {note_id!r}"
        )
    logger.info("read_note: ALLOW note://%s owner=%s", note_id, requester)
    return note["content"]


def main() -> None:
    configure_logging()
    logger.info(
        "producer listening on %s (issuer=%s)",
        producer_settings.base_url,
        producer_settings.idp_issuer,
    )
    mcp.run(transport="http", port=producer_settings.port)


if __name__ == "__main__":
    main()
