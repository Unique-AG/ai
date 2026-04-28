#!/usr/bin/env python3
"""Debug OAuth discovery and tool listing for a remote MCP server.

Usage:
    uv run --with fastmcp --with httpx tutorials/mcp/client_scripts/debug_mcp_auth.py https://example.com/my-server/
    uv run --with fastmcp --with httpx tutorials/mcp/client_scripts/debug_mcp_auth.py --server-url https://example.com/my-server/mcp
    DEBUG_MCP_AUTH_SERVER_URL=https://example.com/my-server/ uv run --with fastmcp --with httpx tutorials/mcp/client_scripts/debug_mcp_auth.py

The script first performs read-only HTTP discovery checks, then lets FastMCP's
OAuth client connect to the MCP endpoint and list tools.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from collections.abc import AsyncGenerator, Iterable, Iterator, Sequence
from contextlib import aclosing, contextmanager
from types import TracebackType
from typing import Literal, Protocol, TypeAlias, cast, override
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse

import httpx
from fastmcp import Client as _FastMCPClient  # pyright: ignore[reportMissingImports, reportUnknownVariableType]
from fastmcp.client.auth import OAuth as _FastMCPOAuth  # pyright: ignore[reportMissingImports, reportUnknownVariableType]


JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
AuthMode: TypeAlias = Literal["oauth", "none"]
FastMCPAuth: TypeAlias = Literal["oauth"] | None


class MCPTool(Protocol):
    name: str
    description: object | None
    inputSchema: object | None
    input_schema: object | None


class MCPClientSession(Protocol):
    async def __aenter__(self) -> "MCPClientSession": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    async def list_tools(self) -> Sequence[MCPTool]: ...


class MCPClientFactory(Protocol):
    def __call__(self, mcp_url: str, *, auth: object | None) -> MCPClientSession: ...


Client = cast(MCPClientFactory, _FastMCPClient)
FastMCPOAuth = cast(type[httpx.Auth], _FastMCPOAuth)

DEFAULT_MCP_PATH = "mcp"
DEFAULT_PROTOCOL_VERSION = "2025-11-25"
DEFAULT_CLIENT_NAME = "debug-mcp-auth"
DEFAULT_CLIENT_VERSION = "0.1.0"
DEFAULT_BODY_PREVIEW_CHARS = 4_000
SERVER_URL_ENV_VAR = "DEBUG_MCP_AUTH_SERVER_URL"
SENSITIVE_HEADER_NAMES = {"authorization", "cookie", "proxy-authorization", "set-cookie"}
SENSITIVE_BODY_KEYS = {
    "access_token",
    "assertion",
    "client_secret",
    "code",
    "id_token",
    "refresh_token",
    "token",
}


def print_step(title: str) -> None:
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}")


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}")


def redact_header_value(name: str, value: str) -> str:
    if name.lower() in SENSITIVE_HEADER_NAMES:
        return "<redacted>"
    return value


def print_headers(headers: httpx.Headers) -> None:
    if not headers:
        print("  <none>")
        return

    for name, value in headers.multi_items():
        print(f"  {name}: {redact_header_value(name, value)}")


def redact_json_value(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if key.lower() in SENSITIVE_BODY_KEYS else redact_json_value(nested_value)
            for key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [redact_json_value(item) for item in value]
    return value


def redact_form_body(content: bytes) -> bytes | None:
    try:
        pairs = parse_qsl(content.decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError:
        return None

    redacted_pairs = [
        (key, "<redacted>" if key.lower() in SENSITIVE_BODY_KEYS else value)
        for key, value in pairs
    ]
    return urlencode(redacted_pairs).encode()


def redact_body_content(content: bytes, content_type: str | None) -> bytes:
    if not content:
        return content

    normalized_content_type = (content_type or "").lower()
    if "json" in normalized_content_type:
        try:
            payload = cast(JsonValue, json.loads(content))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return content
        return json.dumps(redact_json_value(payload), sort_keys=True).encode()

    if "application/x-www-form-urlencoded" in normalized_content_type:
        return redact_form_body(content) or content

    return content


def request_content(request: httpx.Request) -> bytes:
    try:
        return request.content
    except httpx.RequestNotRead:
        return b""


def body_preview(content: bytes, limit: int, *, content_type: str | None = None) -> str:
    content = redact_body_content(content, content_type)
    if not content:
        return "<empty>"
    if limit <= 0:
        return f"<{len(content)} bytes omitted>"

    preview = content[:limit].decode("utf-8", errors="replace")
    suffix = "" if len(content) <= limit else f"\n... <truncated {len(content) - limit} bytes>"
    return preview.replace("\n", "\\n") + suffix


def print_http_exchange(response: httpx.Response, *, body_preview_chars: int) -> None:
    request = response.request
    request_content_type = cast(str | None, request.headers.get("content-type"))
    response_content_type = cast(str | None, response.headers.get("content-type"))
    print(f"\nHTTP exchange: {request.method} {request.url}")
    print("request headers:")
    print_headers(request.headers)
    print("request body:")
    print(body_preview(request_content(request), body_preview_chars, content_type=request_content_type))

    print(f"response status: {response.status_code} {response.reason_phrase}")
    print("response headers:")
    print_headers(response.headers)
    location = cast(str | None, response.headers.get("location"))
    if location:
        print_kv("redirect location", location)
    print("response body:")
    print(body_preview(response.content, body_preview_chars, content_type=response_content_type))


def print_http_response_head(response: httpx.Response, *, body_preview_chars: int) -> None:
    request = response.request
    request_content_type = cast(str | None, request.headers.get("content-type"))
    print(f"\nHTTP exchange: {request.method} {request.url}")
    print("request headers:")
    print_headers(request.headers)
    print("request body:")
    print(body_preview(request_content(request), body_preview_chars, content_type=request_content_type))
    print(f"response status: {response.status_code} {response.reason_phrase}")
    print("response headers:")
    print_headers(response.headers)
    location = cast(str | None, response.headers.get("location"))
    if location:
        print_kv("redirect location", location)
    print("response body: <streaming body not read>")


async def print_auth_flow_response(response: httpx.Response, *, body_preview_chars: int) -> None:
    content_type = cast(str | None, response.headers.get("content-type"))
    if content_type and "text/event-stream" in content_type:
        print_http_response_head(response, body_preview_chars=body_preview_chars)
        return

    _ = await response.aread()
    print_http_exchange(response, body_preview_chars=body_preview_chars)


def is_auth_flow_exchange(response: httpx.Response) -> bool:
    if response.status_code in (401, 403):
        return True

    path = response.request.url.path
    return (
        "/.well-known/" in path
        or path.endswith("/register")
        or path.endswith("/token")
    )


class TracingOAuth(FastMCPOAuth):  # type: ignore[misc, valid-type]
    _body_preview_chars: int

    def __init__(self, *, body_preview_chars: int) -> None:
        super().__init__()
        self._body_preview_chars = body_preview_chars

    @override
    async def async_auth_flow(self, request: httpx.Request) -> AsyncGenerator[httpx.Request, httpx.Response]:
        async with aclosing(super().async_auth_flow(request)) as auth_flow:
            while True:
                try:
                    next_request = await anext(auth_flow)
                except StopAsyncIteration:
                    return

                while True:
                    response = yield next_request
                    if is_auth_flow_exchange(response):
                        print("\nOAuth auth-flow exchange")
                        await print_auth_flow_response(response, body_preview_chars=self._body_preview_chars)
                    try:
                        next_request = await auth_flow.asend(response)
                    except StopAsyncIteration:
                        return


@contextmanager
def trace_httpx_async_clients(body_preview_chars: int) -> Iterator[None]:
    original_async_client = httpx.AsyncClient

    class TracedAsyncClient(original_async_client):  # type: ignore[misc, valid-type]
        @override
        async def send(
            self,
            request: httpx.Request,
            *,
            stream: bool = False,
            auth: httpx._types.AuthTypes | httpx._client.UseClientDefault | None = httpx.USE_CLIENT_DEFAULT,  # pyright: ignore[reportPrivateUsage]
            follow_redirects: bool | httpx._client.UseClientDefault = httpx.USE_CLIENT_DEFAULT,  # pyright: ignore[reportPrivateUsage]
        ) -> httpx.Response:
            response = await super().send(
                request,
                stream=stream,
                auth=auth,
                follow_redirects=follow_redirects,
            )
            if stream:
                print_http_response_head(response, body_preview_chars=body_preview_chars)
                return response

            _ = await response.aread()
            print_http_exchange(response, body_preview_chars=body_preview_chars)
            return response

    httpx.AsyncClient = cast(type[httpx.AsyncClient], TracedAsyncClient)
    try:
        yield
    finally:
        httpx.AsyncClient = original_async_client


async def send_traced(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    body_preview_chars: int,
    headers: dict[str, str] | None = None,
    json_body: JsonObject | None = None,
) -> httpx.Response:
    print(f"\n--> {method} {url}")
    try:
        response = await client.request(method, url, headers=headers, json=json_body)
    except httpx.HTTPError as exc:
        print_kv("request error", f"{type(exc).__name__}: {exc}")
        raise

    print_http_exchange(response, body_preview_chars=body_preview_chars)
    return response


def build_initialize_request(protocol_version: str, client_name: str, client_version: str) -> JsonObject:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": {"name": client_name, "version": client_version},
        },
    }


def normalize_mcp_url(server_url: str, mcp_path: str) -> str:
    """Return the concrete MCP endpoint URL.

    Accepts either the final MCP endpoint (`.../mcp-risk/mcp`) or the public
    server prefix (`.../mcp-risk/`) and appends `mcp_path` in the latter case.
    """
    parsed = urlparse(server_url)
    path = parsed.path.rstrip("/")
    if path.endswith(f"/{mcp_path.strip('/')}"):
        return server_url.rstrip("/")
    return urljoin(server_url.rstrip("/") + "/", mcp_path.strip("/"))


def origin_for(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def dedupe(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def parse_www_authenticate_resource_metadata(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r'resource_metadata="([^"]+)"', value)
    return match.group(1) if match else None


async def request_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    body_preview_chars: int,
    headers: dict[str, str] | None = None,
) -> tuple[int | None, JsonObject | None, str | None]:
    try:
        response = await send_traced(
            client,
            "GET",
            url,
            body_preview_chars=body_preview_chars,
            headers=headers,
        )
    except httpx.HTTPError as exc:
        return None, None, f"{type(exc).__name__}: {exc}"

    content_type = cast(str, response.headers.get("content-type", ""))
    if "json" not in content_type:
        preview = response.text[:300].replace("\n", "\\n")
        return response.status_code, None, f"non-json content-type={content_type!r} body={preview!r}"

    try:
        return response.status_code, cast(JsonObject, response.json()), None
    except json.JSONDecodeError as exc:
        return response.status_code, None, f"invalid json: {exc}"


async def probe_unauthenticated_mcp(
    client: httpx.AsyncClient,
    mcp_url: str,
    *,
    protocol_version: str,
    client_name: str,
    client_version: str,
    body_preview_chars: int,
) -> str | None:
    print_step("1. Probe MCP endpoint without Authorization")

    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-protocol-version": protocol_version,
    }

    initialize_request = build_initialize_request(protocol_version, client_name, client_version)
    response = await send_traced(
        client,
        "POST",
        mcp_url,
        body_preview_chars=body_preview_chars,
        headers=headers,
        json_body=initialize_request,
    )
    content_type = cast(str | None, response.headers.get("content-type"))
    www_authenticate = cast(str | None, response.headers.get("www-authenticate"))
    print_kv("probe content-type", content_type)
    print_kv("probe www-authenticate", www_authenticate)

    resource_metadata = parse_www_authenticate_resource_metadata(www_authenticate)
    print_kv("advertised resource_metadata", resource_metadata)
    return resource_metadata


async def inspect_metadata(
    client: httpx.AsyncClient,
    mcp_url: str,
    advertised_url: str | None,
    *,
    body_preview_chars: int,
) -> None:
    print_step("2. Inspect protected-resource metadata candidates")

    parsed = urlparse(mcp_url)
    origin = origin_for(mcp_url)
    mcp_path = parsed.path.rstrip("/")
    public_prefix, _, mcp_leaf = mcp_path.rpartition("/")

    candidates = dedupe(
        [
            advertised_url,
            f"{origin}/.well-known/oauth-protected-resource{mcp_path}",
            f"{origin}{public_prefix}/.well-known/oauth-protected-resource/{mcp_leaf}",
            f"{origin}/.well-known/oauth-protected-resource/{mcp_leaf}",
        ]
    )

    authorization_servers: list[str] = []
    for index, url in enumerate(candidates, start=1):
        print(f"\nProtected-resource metadata candidate {index}: {url}")
        status, payload, error = await request_json(client, url, body_preview_chars=body_preview_chars)
        print_kv("parsed status", status)
        if error:
            print_kv("parse error", error)
            continue
        print("parsed JSON:")
        print(json.dumps(payload, indent=2, sort_keys=True))
        auth_servers = payload.get("authorization_servers", []) if payload else []
        if isinstance(auth_servers, list):
            authorization_servers.extend(str(server) for server in auth_servers)

    print_step("3. Inspect authorization-server metadata candidates")
    auth_server_candidates = dedupe(
        [
            *authorization_servers,
            f"{origin}{public_prefix}/.well-known/openid-configuration",
            f"{origin}{public_prefix}/.well-known/oauth-authorization-server",
            f"{origin}/.well-known/openid-configuration",
            f"{origin}/.well-known/oauth-authorization-server",
        ]
    )

    for base_or_metadata_url in auth_server_candidates:
        urls = (
            [base_or_metadata_url]
            if "/.well-known/" in base_or_metadata_url
            else [
                base_or_metadata_url.rstrip("/") + "/.well-known/openid-configuration",
                base_or_metadata_url.rstrip("/") + "/.well-known/oauth-authorization-server",
            ]
        )
        for index, url in enumerate(dedupe(urls), start=1):
            print(f"\nAuthorization-server metadata candidate {index}: {url}")
            status, payload, error = await request_json(client, url, body_preview_chars=body_preview_chars)
            print_kv("parsed status", status)
            if error:
                print_kv("parse error", error)
                continue
            print("parsed JSON:")
            print(json.dumps(payload, indent=2, sort_keys=True))


async def connect_with_fastmcp(mcp_url: str, auth: FastMCPAuth, *, body_preview_chars: int) -> None:
    print_step("4. Connect with FastMCP OAuth client and list tools")
    print_kv("mcp_url", mcp_url)
    print_kv("auth", auth or "none")
    if auth == "oauth":
        print("FastMCP may open a browser or print a login URL. Complete that flow when prompted.")

    fastmcp_auth: object | None = TracingOAuth(body_preview_chars=body_preview_chars) if auth == "oauth" else None
    with trace_httpx_async_clients(body_preview_chars):
        async with Client(mcp_url, auth=fastmcp_auth) as mcp_client:
            print("\nConnected.")
            tools = await mcp_client.list_tools()

    print_step("5. Tools")
    if not tools:
        print("No tools returned.")
        return

    for index, tool in enumerate(tools, start=1):
        print(f"\n[{index}] {tool.name}")
        description = getattr(tool, "description", None)
        if description:
            print(f"    description: {description}")
        input_schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None)
        if input_schema:
            print("    input schema:")
            print(json.dumps(input_schema, indent=6, sort_keys=True))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _ = parser.add_argument(
        "server_url",
        nargs="?",
        help="MCP server prefix or final /mcp endpoint.",
    )
    _ = parser.add_argument(
        "--server-url",
        dest="server_url_option",
        metavar="SERVER_URL",
        help=f"MCP server prefix or final /mcp endpoint. Overrides {SERVER_URL_ENV_VAR}.",
    )
    _ = parser.add_argument(
        "--mcp-path",
        default=DEFAULT_MCP_PATH,
        help="Path appended when server_url is a prefix. Default: mcp",
    )
    _ = parser.add_argument(
        "--protocol-version",
        default=DEFAULT_PROTOCOL_VERSION,
        help=f"MCP protocol version used by the unauthenticated probe. Default: {DEFAULT_PROTOCOL_VERSION}",
    )
    _ = parser.add_argument(
        "--client-name",
        default=DEFAULT_CLIENT_NAME,
        help=f"clientInfo.name sent by the unauthenticated initialize probe. Default: {DEFAULT_CLIENT_NAME}",
    )
    _ = parser.add_argument(
        "--client-version",
        default=DEFAULT_CLIENT_VERSION,
        help=f"clientInfo.version sent by the unauthenticated initialize probe. Default: {DEFAULT_CLIENT_VERSION}",
    )
    _ = parser.add_argument(
        "--auth",
        choices=("oauth", "none"),
        default="oauth",
        help="FastMCP auth mode for the final tool-listing connection. Default: oauth",
    )
    _ = parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds for metadata probes.",
    )
    _ = parser.add_argument(
        "--body-preview-chars",
        type=int,
        default=DEFAULT_BODY_PREVIEW_CHARS,
        help=f"Request/response body characters to print for each traced HTTP exchange. Default: {DEFAULT_BODY_PREVIEW_CHARS}",
    )
    _ = parser.add_argument(
        "--debug-logs",
        action="store_true",
        help="Enable DEBUG logging for FastMCP/httpx internals during the OAuth connection.",
    )
    namespace = parser.parse_args()

    server_url_arg = cast(str | None, namespace.server_url)
    server_url_option = cast(str | None, namespace.server_url_option)
    mcp_path = cast(str, namespace.mcp_path)
    protocol_version = cast(str, namespace.protocol_version)
    client_name = cast(str, namespace.client_name)
    client_version = cast(str, namespace.client_version)
    auth_mode = cast(AuthMode, namespace.auth)
    timeout = cast(float, namespace.timeout)
    body_preview_chars = cast(int, namespace.body_preview_chars)
    debug_logs = cast(bool, namespace.debug_logs)

    if server_url_arg and server_url_option:
        parser.error("provide the server URL either positionally or with --server-url, not both")

    server_url = server_url_option or server_url_arg or os.getenv(SERVER_URL_ENV_VAR)
    if not server_url:
        parser.error(f"server URL required. Provide it positionally, with --server-url, or via {SERVER_URL_ENV_VAR}.")

    logging.basicConfig(
        level=logging.DEBUG if debug_logs else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    mcp_url = normalize_mcp_url(server_url, mcp_path)
    fastmcp_auth: FastMCPAuth = None if auth_mode == "none" else auth_mode

    print_step("0. Configuration")
    print_kv("input server_url", server_url)
    print_kv("normalized mcp_url", mcp_url)
    print_kv("mcp_path", mcp_path)
    print_kv("protocol_version", protocol_version)
    print_kv("client_name", client_name)
    print_kv("client_version", client_version)
    print_kv("body_preview_chars", body_preview_chars)

    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as http_client:
        advertised = await probe_unauthenticated_mcp(
            http_client,
            mcp_url,
            protocol_version=protocol_version,
            client_name=client_name,
            client_version=client_version,
            body_preview_chars=body_preview_chars,
        )
        await inspect_metadata(
            http_client,
            mcp_url,
            advertised,
            body_preview_chars=body_preview_chars,
        )

    await connect_with_fastmcp(mcp_url, fastmcp_auth, body_preview_chars=body_preview_chars)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
