#!/usr/bin/env python3
"""Verbose OAuth MCP client for debugging the Knowledge Base Search server.

Runs discovery probes, then completes a full FastMCP OAuth browser login while
printing every auth-related HTTP exchange (including decoded JWTs). After
auth succeeds it lists tools and optionally calls ``search``.

Usage (from this directory)::

    uv run python debug_auth_client.py
    uv run python debug_auth_client.py --url https://unique-search-mcp.azurewebsites.net/mcp
    uv run python debug_auth_client.py --url http://localhost:8003/mcp --query "what is unique?"
    uv run python debug_auth_client.py --no-search   # auth + list_tools only
    uv run python debug_auth_client.py --debug-logs

Tokens are kept in-memory for this process only (no Inspector-style localStorage),
so each run starts a clean OAuth registration.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import hashlib
import json
import logging
import sys
from collections.abc import AsyncGenerator, Iterator
from contextlib import aclosing, contextmanager
from datetime import datetime, timezone
from typing import Any, cast
from urllib.parse import urlparse

import httpx
from fastmcp import Client
from fastmcp.client.auth import OAuth

DEFAULT_MCP_URL = "https://unique-search-mcp.azurewebsites.net/mcp"
DEFAULT_QUERY = "what is unique?"
DEFAULT_BODY_PREVIEW = 6_000
DEFAULT_CALLBACK_PORT = 8765

_JWT_SEEN: set[str] = set()


# ── printing helpers ─────────────────────────────────────────────────────────


def step(title: str) -> None:
    print(f"\n{'=' * 88}\n{title}\n{'=' * 88}", flush=True)


def kv(key: str, value: object) -> None:
    print(f"{key}: {value}", flush=True)


def headers(h: httpx.Headers) -> None:
    if not h:
        print("  <none>", flush=True)
        return
    for name, value in h.multi_items():
        lower = name.lower()
        if lower in {"authorization", "cookie", "set-cookie"}:
            # Show presence + shape, not the full secret.
            print(f"  {name}: <redacted len={len(value)}>", flush=True)
        else:
            print(f"  {name}: {value}", flush=True)


def preview(content: bytes, limit: int) -> str:
    if not content:
        return "<empty>"
    text = content[:limit].decode("utf-8", errors="replace")
    if len(content) > limit:
        text += f"\n... <truncated {len(content) - limit} bytes>"
    return text


def _b64url_json(segment: str) -> dict[str, Any] | None:
    try:
        raw = base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
        obj = json.loads(raw.decode("utf-8", errors="replace"))
    except (ValueError, binascii.Error, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _epoch(value: object) -> str | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def decode_jwt(token: str, label: str) -> None:
    fp = hashlib.sha256(token.encode("ascii", errors="replace")).hexdigest()[:16]
    if fp in _JWT_SEEN:
        print(f"  {label}: <same JWT as before, fp={fp}>", flush=True)
        return
    _JWT_SEEN.add(fp)
    parts = token.split(".")
    if len(parts) != 3:
        print(f"  {label}: <opaque, {len(token)} chars, fp={fp}>", flush=True)
        return
    print(f"  {label} fp: {fp}", flush=True)
    header = _b64url_json(parts[0])
    claims = _b64url_json(parts[1])
    if header:
        print(f"  {label} header:", flush=True)
        print(json.dumps(header, indent=2, sort_keys=True), flush=True)
    if claims:
        print(f"  {label} claims:", flush=True)
        print(json.dumps(claims, indent=2, sort_keys=True), flush=True)
        for key in ("iat", "nbf", "exp", "auth_time"):
            human = _epoch(claims.get(key))
            if human:
                print(f"  {label} {key}: {claims[key]} ({human})", flush=True)
        # Highlight identity claims we care about for search.
        for key in (
            "sub",
            "email",
            "preferred_username",
            "urn:zitadel:iam:user:resourceowner:id",
            "aud",
            "iss",
            "client_id",
            "scope",
            "scp",
        ):
            if key in claims:
                print(f"  ★ {label}.{key} = {claims[key]!r}", flush=True)


def exchange(
    response: httpx.Response, *, body_limit: int, stream: bool = False
) -> None:
    req = response.request
    print(f"\n── HTTP {req.method} {req.url}", flush=True)
    print("request headers:", flush=True)
    headers(req.headers)
    try:
        body = req.content
    except httpx.RequestNotRead:
        body = b""
    print("request body:", flush=True)
    print(preview(body, body_limit), flush=True)

    print(f"response: {response.status_code} {response.reason_phrase}", flush=True)
    print("response headers:", flush=True)
    headers(response.headers)
    loc = response.headers.get("location")
    if loc:
        kv("redirect →", loc)

    if stream:
        print("response body: <streaming, not buffered>", flush=True)
    else:
        print("response body:", flush=True)
        print(preview(response.content, body_limit), flush=True)

    auth = req.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        print("decoded request bearer:", flush=True)
        decode_jwt(auth[7:].strip(), "access_token")

    # Decode tokens from /token responses.
    if req.url.path.rstrip("/").endswith("/token") and response.status_code == 200:
        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, dict):
            print("decoded /token response:", flush=True)
            for key in (
                "token_type",
                "scope",
                "expires_in",
                "refresh_expires_in",
                "session_state",
            ):
                if key in payload:
                    kv(f"  {key}", payload[key])
            for key in ("access_token", "id_token"):
                val = payload.get(key)
                if isinstance(val, str) and val:
                    decode_jwt(val, key)
            refresh = payload.get("refresh_token")
            if isinstance(refresh, str) and refresh:
                if refresh.count(".") == 2:
                    decode_jwt(refresh, "refresh_token")
                else:
                    kv("  refresh_token", f"<opaque, {len(refresh)} chars>")


# ── HTTP tracing ─────────────────────────────────────────────────────────────


def _is_auth_exchange(response: httpx.Response) -> bool:
    if response.status_code in (401, 403):
        return True
    path = response.request.url.path
    return (
        "/.well-known/" in path
        or path.endswith("/register")
        or path.endswith("/token")
        or path.endswith("/authorize")
        or "/consent" in path
        or path.endswith("/auth/callback")
        or "/oauth/" in path
        or "/oidc/" in path
    )


class TracingOAuth(OAuth):
    """FastMCP OAuth that dumps every auth-related HTTP exchange."""

    def __init__(self, mcp_url: str, *, body_limit: int, callback_port: int) -> None:
        super().__init__(
            mcp_url=mcp_url,
            client_name="mcp-search-debug-auth-client",
            callback_port=callback_port,
            # Explicit scopes so DCR + authorize match what the server advertises.
            scopes=[
                "openid",
                "profile",
                "email",
                "mcp:tools",
                "mcp:prompts",
                "mcp:resources",
                "mcp:resource-templates",
                "urn:zitadel:iam:user:resourceowner",
            ],
        )
        self._body_limit = body_limit

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        async with aclosing(super().async_auth_flow(request)) as flow:
            while True:
                try:
                    next_request = await anext(flow)
                except StopAsyncIteration:
                    return
                while True:
                    response = yield next_request
                    if _is_auth_exchange(response):
                        print("\n[OAuth auth-flow exchange]", flush=True)
                        content_type = response.headers.get("content-type", "")
                        if "text/event-stream" in content_type:
                            exchange(response, body_limit=self._body_limit, stream=True)
                        else:
                            await response.aread()
                            exchange(response, body_limit=self._body_limit)
                    try:
                        next_request = await flow.asend(response)
                    except StopAsyncIteration:
                        return


@contextmanager
def trace_all_httpx(body_limit: int) -> Iterator[None]:
    """Monkey-patch httpx.AsyncClient so every exchange is logged."""
    original = httpx.AsyncClient

    class Traced(original):  # type: ignore[misc, valid-type]
        async def send(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:  # type: ignore[override]
            stream = bool(kwargs.get("stream", False))
            response = await super().send(request, **kwargs)
            if stream:
                exchange(response, body_limit=body_limit, stream=True)
            else:
                await response.aread()
                exchange(response, body_limit=body_limit)
            return response

    httpx.AsyncClient = cast(type[httpx.AsyncClient], Traced)
    try:
        yield
    finally:
        httpx.AsyncClient = original


# ── discovery probes ─────────────────────────────────────────────────────────


async def probe_unauthenticated(
    mcp_url: str, *, body_limit: int, timeout: float
) -> None:
    step("1. Unauthenticated POST /mcp (expect 401 + WWW-Authenticate)")
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
        resp = await client.post(
            mcp_url,
            headers={
                "accept": "application/json, text/event-stream",
                "content-type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "mcp-search-debug-auth-client",
                        "version": "0.1.0",
                    },
                },
            },
        )
        exchange(resp, body_limit=body_limit)
        www = resp.headers.get("www-authenticate")
        kv("WWW-Authenticate", www)


async def probe_metadata(mcp_url: str, *, body_limit: int, timeout: float) -> None:
    step("2. OAuth discovery metadata")
    origin = f"{urlparse(mcp_url).scheme}://{urlparse(mcp_url).netloc}"
    urls = [
        f"{origin}/.well-known/oauth-protected-resource/mcp",
        f"{origin}/.well-known/oauth-authorization-server",
        f"{origin}/.well-known/openid-configuration",
        f"{origin}/health",
    ]
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
        for url in urls:
            print(f"\n--> GET {url}", flush=True)
            try:
                resp = await client.get(url)
            except httpx.HTTPError as exc:
                kv("error", f"{type(exc).__name__}: {exc}")
                continue
            exchange(resp, body_limit=body_limit)
            if "json" in resp.headers.get("content-type", ""):
                try:
                    payload = resp.json()
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict) and "scopes_supported" in payload:
                    kv("★ scopes_supported", payload.get("scopes_supported"))
                if isinstance(payload, dict) and "authorization_endpoint" in payload:
                    kv(
                        "★ authorization_endpoint",
                        payload.get("authorization_endpoint"),
                    )
                    kv("★ token_endpoint", payload.get("token_endpoint"))
                    kv("★ registration_endpoint", payload.get("registration_endpoint"))


# ── authenticated MCP session ────────────────────────────────────────────────


async def connect_and_exercise(
    mcp_url: str,
    *,
    query: str | None,
    body_limit: int,
    callback_port: int,
) -> None:
    step("3. FastMCP OAuth connect (browser login)")
    kv("mcp_url", mcp_url)
    kv("callback_port", callback_port)
    kv(
        "note",
        "A browser window should open. Approve the MCP consent page, then log in at Zitadel.",
    )

    oauth = TracingOAuth(mcp_url, body_limit=body_limit, callback_port=callback_port)

    with trace_all_httpx(body_limit):
        async with Client(mcp_url, auth=oauth) as client:
            step("4. Authenticated — list tools")
            tools = await client.list_tools()
            for i, tool in enumerate(tools, 1):
                print(f"\n[{i}] {tool.name}", flush=True)
                if tool.description:
                    print(f"    description: {tool.description}", flush=True)
                meta = getattr(tool, "meta", None) or getattr(tool, "_meta", None)
                if meta:
                    print("    tool meta:", flush=True)
                    print(json.dumps(meta, indent=2, default=str), flush=True)

            if query is None:
                print("\n(--no-search: skipping tool call)", flush=True)
                return

            step(f"5. Call search(search_string={query!r})")
            result = await client.call_tool("search", {"search_string": query})
            is_error = getattr(result, "isError", False)
            kv("isError", is_error)
            content = getattr(result, "content", []) or []
            kv("content_items", len(content))
            for i, item in enumerate(content, 1):
                text = getattr(item, "text", str(item))
                print(f"\n--- result [{i}] ---", flush=True)
                print(
                    text[:2_000] if isinstance(text, str) else str(text)[:2_000],
                    flush=True,
                )
                item_meta = getattr(item, "meta", None) or getattr(item, "_meta", None)
                if item_meta:
                    print("item _meta keys:", sorted(item_meta.keys()), flush=True)
                    ref = item_meta.get("unique.app/reference")
                    if ref:
                        print("unique.app/reference:", flush=True)
                        print(json.dumps(ref, indent=2, default=str), flush=True)


# ── main ─────────────────────────────────────────────────────────────────────


async def amain(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_MCP_URL,
        help=f"MCP endpoint URL (default: {DEFAULT_MCP_URL})",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help=f"search_string for the search tool (default: {DEFAULT_QUERY!r})",
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="Stop after list_tools (do not call search).",
    )
    parser.add_argument(
        "--callback-port",
        type=int,
        default=DEFAULT_CALLBACK_PORT,
        help=f"Local OAuth callback port (default: {DEFAULT_CALLBACK_PORT})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout for discovery probes.",
    )
    parser.add_argument(
        "--body-preview-chars",
        type=int,
        default=DEFAULT_BODY_PREVIEW,
        help="Max chars of each request/response body to print.",
    )
    parser.add_argument(
        "--debug-logs",
        action="store_true",
        help="Enable DEBUG logging for httpx/fastmcp/mcp.",
    )
    parser.add_argument(
        "--skip-probes",
        action="store_true",
        help="Skip unauthenticated discovery probes; go straight to OAuth.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug_logs else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.debug_logs:
        for name in ("httpx", "httpcore", "mcp", "fastmcp", "authlib"):
            logging.getLogger(name).setLevel(logging.DEBUG)

    mcp_url = args.url.rstrip("/")
    if not mcp_url.endswith("/mcp"):
        # Allow passing the host root.
        if (
            mcp_url.endswith(".net")
            or mcp_url.endswith(".app")
            or mcp_url.count("/") <= 2
        ):
            mcp_url = mcp_url + "/mcp"

    step("0. Configuration")
    kv("mcp_url", mcp_url)
    kv("callback_port", args.callback_port)
    kv("query", None if args.no_search else args.query)
    kv("token_storage", "in-memory (fresh registration every process)")
    kv(
        "tip",
        "If the browser never opens, watch this terminal for a printed authorize URL.",
    )

    if not args.skip_probes:
        await probe_unauthenticated(
            mcp_url, body_limit=args.body_preview_chars, timeout=args.timeout
        )
        await probe_metadata(
            mcp_url, body_limit=args.body_preview_chars, timeout=args.timeout
        )

    await connect_and_exercise(
        mcp_url,
        query=None if args.no_search else args.query,
        body_limit=args.body_preview_chars,
        callback_port=args.callback_port,
    )
    step("Done")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(amain()))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
