"""End-to-end demo for the compose variant (Keycloak + Dex).

All servers run inside Docker so every URL uses Docker service names.
This script is executed by the `demo` container defined in docker-compose.yml
after producer and consumer healthchecks pass.

Flow
----
1. Obtain Alice's Dex token via ROPC (password) grant.
2. Exchange it at Keycloak (discovered via producer's RFC 9728 metadata) for a
   producer-audience token.
3. Create a note on the producer as Alice.
4. Ask the consumer to archive that note on Alice's behalf.
5. Repeat step 4 as Bob → expect denial.

Display
-------
Dex issues an opaque ``sub`` claim (base64-encoded connector+userID).  Keycloak
federates the user and issues producer tokens with the federated Keycloak UUID
as ``sub``.  Both values are consistent *per user*, so ownership enforcement
works correctly.  ``preferred_username`` is used for human-readable output.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os

import httpx
from fastmcp import Client
from fastmcp.client.auth import BearerAuth

from mcp_resource_sharing.common.clients import client_settings
from mcp_resource_sharing.common.logging_setup import configure_logging
from mcp_resource_sharing.common.token_exchange import obtain_producer_token
from mcp_resource_sharing.consumer.settings import consumer_settings
from mcp_resource_sharing.producer.settings import producer_settings

logger = logging.getLogger("rp.demo")

# Dex token URL — injected by docker-compose.yml; falls back for local testing.
DEX_TOKEN_URL = os.environ.get("DEX_TOKEN_URL", "http://dex:5556/token")


def _decode_jwt_payload(token: str) -> dict:
    """Decode the JWT payload without signature verification (display only)."""
    try:
        payload_b64 = token.split(".")[1]
        # Add padding so base64 doesn't complain.
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:  # noqa: BLE001
        return {}


def _display_name(token: str) -> str:
    """Return the human-readable username from a JWT token (best-effort)."""
    claims = _decode_jwt_payload(token)
    return (
        claims.get("preferred_username")
        or claims.get("email", "").split("@")[0]
        or claims.get("sub", "unknown")
    )


async def _password_grant(client_id: str, username: str, password: str) -> str:
    """Obtain an access token from Dex via the Resource Owner Password grant."""
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            DEX_TOKEN_URL,
            data={
                "grant_type": "password",
                "client_id": client_id,
                "username": username,
                "password": password,
                "scope": "openid profile email",
            },
        )
        resp.raise_for_status()
    return resp.json()["access_token"]


async def _run_demo() -> None:
    configure_logging()
    producer_url = str(producer_settings.mcp_url)
    consumer_url = str(consumer_settings.mcp_url)

    print("=" * 60)
    print("  cross-IdP resource pipeline — compose demo")
    print("  Consumer IdP : Dex  (http://dex:5556)")
    print("  Producer IdP : Keycloak  (http://keycloak:8080/realms/producer)")
    print("=" * 60)

    # ── 1. Obtain user tokens from Dex (password grant) ───────────────── #
    logger.info("obtaining Dex tokens for alice and bob …")
    alice_dex_token = await _password_grant(
        client_settings.demo_app_id, "alice@consumer.local", "alice123"
    )
    bob_dex_token = await _password_grant(
        client_settings.demo_app_id, "bob@consumer.local", "bob123"
    )

    alice_name = _display_name(alice_dex_token)
    bob_name = _display_name(bob_dex_token)
    print(
        f"\n[dex] alice token  sub={_decode_jwt_payload(alice_dex_token).get('sub')!r}  preferred_username={alice_name!r}"
    )
    print(
        f"[dex] bob   token  sub={_decode_jwt_payload(bob_dex_token).get('sub')!r}  preferred_username={bob_name!r}"
    )

    # ── 2. Alice: exchange Dex token for a producer token ─────────────── #
    #    obtain_producer_token discovers Keycloak via RFC 9728 → RFC 8414.
    logger.info("alice: discovering producer IdP and exchanging token …")
    alice_producer_token = await obtain_producer_token(
        producer_url, alice_dex_token, client_settings.demo_app_id
    )
    alice_kc_claims = _decode_jwt_payload(alice_producer_token)
    print(
        f"\n[keycloak] alice producer token"
        f"  sub={alice_kc_claims.get('sub')!r}"
        f"  preferred_username={alice_kc_claims.get('preferred_username')!r}"
        f"  aud={alice_kc_claims.get('aud')!r}"
    )

    # ── 3. Alice creates a note on the producer ────────────────────────── #
    async with Client(producer_url, auth=BearerAuth(alice_producer_token)) as producer:
        created = await producer.call_tool(
            "create_note",
            {"title": "Q3 roadmap", "body": "Confidential planning notes."},
        )
    note_uri = created.data["uri"]
    owner_sub = created.data["owner"]
    print(f"\n[{alice_name}] created {note_uri}  (owner_sub={owner_sub!r})")

    # ── 4. Consumer archives the note on Alice's behalf ───────────────── #
    #    The consumer server internally exchanges Alice's Dex token →
    #    Keycloak producer token (acting as `resource-consumer-service`).
    async with Client(consumer_url, auth=BearerAuth(alice_dex_token)) as consumer:
        result = await consumer.call_tool(
            "archive_note",
            {"producer_url": producer_url, "resource_uri": note_uri},
        )
    print(f"[{alice_name}] archived: {result.data}")

    # ── 5. Bob tries to archive Alice's note → must be denied ─────────── #
    async with Client(consumer_url, auth=BearerAuth(bob_dex_token)) as consumer:
        try:
            await consumer.call_tool(
                "archive_note",
                {"producer_url": producer_url, "resource_uri": note_uri},
            )
            print(
                f"[{bob_name}] archived?!  ownership check FAILED to protect the resource"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[{bob_name}] denied as expected: {exc}")

    print("\n✓ Demo completed successfully")


def main() -> None:
    asyncio.run(_run_demo())


if __name__ == "__main__":
    main()
