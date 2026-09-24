"""Discover the producer's IdP at runtime, then exchange a token for it.

This is the MCP-native way to avoid hardcoding the producer's identity provider.
It is *client-side* logic shared by any confidential client that needs a
producer token — both the consumer server and Alice's desktop app (the demo) use
it:

  1. **RFC 9728** — probe the producer unauthenticated; it answers ``401``,
     usually with ``WWW-Authenticate: Bearer ... resource_metadata="<url>"``.
     Since the 2025-11-25 MCP revision that header is *optional*, so when it is
     absent the client falls back to constructing the well-known URI from the
     producer URL itself. The metadata lists ``authorization_servers``.
  2. **RFC 8414 / OIDC discovery** — fetch the authorization-server metadata
     (``…/oauth-authorization-server`` first, ``…/openid-configuration`` as
     fallback) to learn the producer IdP's ``token_endpoint``.
  3. **RFC 8693** — exchange the user's consumer-IdP token at that endpoint for a
     producer-audience token, naming the target with the RFC 8707 ``resource``
     parameter.

The caller only needs the producer's URL — never the producer IdP's address.
"""

from __future__ import annotations

import logging
import os
import re

import httpx

from mcp_resource_sharing.common.oauth import ACCESS_TOKEN_TYPE, TOKEN_EXCHANGE_GRANT

logger = logging.getLogger("rp.discovery")

_RESOURCE_METADATA_RE = re.compile(r'resource_metadata="([^"]+)"')


def _well_known_prm_urls(producer_url: str) -> list[str]:
    """Candidate RFC 9728 well-known URIs for a resource URL, in spec order.

    For ``http://host/mcp``: first the path-aware
    ``/.well-known/oauth-protected-resource/mcp``, then the root document.
    """
    parsed = httpx.URL(producer_url)
    origin = f"{parsed.scheme}://{parsed.netloc.decode()}"
    path = parsed.path.rstrip("/")
    candidates = []
    if path:
        candidates.append(f"{origin}/.well-known/oauth-protected-resource{path}")
    candidates.append(f"{origin}/.well-known/oauth-protected-resource")
    return candidates


async def _fetch_first_json(http: httpx.AsyncClient, urls: list[str]) -> dict | None:
    for url in urls:
        response = await http.get(url)
        if response.status_code == 200:
            return response.json()
    return None


async def _discover_token_endpoint(http: httpx.AsyncClient, producer_url: str) -> str:
    # 1) Unauthenticated probe -> 401 challenge pointing at resource metadata.
    #    The header is optional (MCP 2025-11-25): fall back to the well-known
    #    URIs derived from the producer URL when it is missing.
    probe = await http.get(producer_url)
    challenge = probe.headers.get("WWW-Authenticate", "")
    match = _RESOURCE_METADATA_RE.search(challenge)
    if match:
        metadata_urls = [match.group(1)]
        logger.info(
            "discovery: probe %s -> %s, resource_metadata=%s",
            producer_url,
            probe.status_code,
            match.group(1),
        )
    else:
        metadata_urls = _well_known_prm_urls(producer_url)
        logger.info(
            "discovery: no resource_metadata in challenge, trying well-known: %s",
            metadata_urls,
        )

    # 2) Protected resource metadata (RFC 9728) -> authorization server(s).
    resource_metadata = await _fetch_first_json(http, metadata_urls)
    if resource_metadata is None:
        raise RuntimeError(
            f"could not fetch protected-resource metadata for {producer_url!r} "
            f"(tried {metadata_urls})"
        )
    issuer = resource_metadata["authorization_servers"][0].rstrip("/")
    logger.info("discovery: RFC 9728 -> authorization_server=%s", issuer)

    # 3) Authorization-server metadata -> token endpoint. Try RFC 8414 first,
    #    then OIDC discovery (both are valid per MCP 2025-11-25).
    as_metadata = await _fetch_first_json(
        http,
        [
            f"{issuer}/.well-known/oauth-authorization-server",
            f"{issuer}/.well-known/openid-configuration",
        ],
    )
    if as_metadata is None:
        raise RuntimeError(f"no authorization-server metadata found for {issuer!r}")
    token_endpoint = as_metadata["token_endpoint"]
    logger.info("discovery: RFC 8414 -> token_endpoint=%s", token_endpoint)
    return token_endpoint


async def obtain_producer_token(
    producer_url: str, subject_token: str, client_id: str
) -> str:
    """Discover the producer's IdP and exchange the user token for a producer token.

    The request sends both RFC 8707 ``resource`` and RFC 8693 ``audience``
    pointing at the same URL. Standard IdPs (including Keycloak) use one or
    the other; sending both maximises compatibility without breaking anything.
    ``requested_token_type`` is included explicitly so IdPs that require it
    (e.g. Keycloak with strict token-exchange validation) do not reject the
    request.
    """
    async with httpx.AsyncClient() as http:
        token_endpoint = await _discover_token_endpoint(http, producer_url)
        logger.info("exchange: POST %s as client_id=%s", token_endpoint, client_id)
        exchange_audience = os.environ.get("RP_TOKEN_EXCHANGE_AUDIENCE") or producer_url
        data: dict[str, str] = {
            "grant_type": TOKEN_EXCHANGE_GRANT,
            "subject_token": subject_token,
            "subject_token_type": ACCESS_TOKEN_TYPE,
            # Explicit requested token type (RFC 8693 §2.1, optional but
            # required by some IdPs to enable the exchange SPI path).
            "requested_token_type": ACCESS_TOKEN_TYPE,
            # RFC 8707 resource indicator: name the target by URL.
            "resource": producer_url,
            # RFC 8693 audience: Keycloak legacy exchange expects the target
            # OAuth client id (resource-producer), not the MCP URL.
            "audience": exchange_audience,
            "client_id": client_id,
        }
        # Keycloak legacy external→internal exchange requires the IdP alias when
        # the subject token is an access token from a brokered provider (Dex).
        subject_issuer = os.environ.get("RP_TOKEN_EXCHANGE_SUBJECT_ISSUER")
        if subject_issuer:
            data["subject_issuer"] = subject_issuer
        response = await http.post(
            token_endpoint,
            data=data,
        )
    logger.info("exchange: %s -> %s", token_endpoint, response.status_code)
    response.raise_for_status()
    return response.json()["access_token"]
