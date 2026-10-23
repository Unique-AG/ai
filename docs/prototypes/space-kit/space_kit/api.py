import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Protocol
from urllib.parse import quote, urlencode

from space_kit.base import (
    JsonObject,
    JsonValue,
    KitModel,
    SpaceKitError,
    as_list,
    as_object,
)
from space_kit.env import Credentials

API_VERSION = "2023-12-06"
TIMEOUT_S = 60
ERROR_BODY_CHARS = 600


class HttpResponse(KitModel):
    status: int
    body: JsonValue


class Transport(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: JsonValue,
    ) -> HttpResponse: ...


class UrllibTransport:
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: JsonValue,
    ) -> HttpResponse:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url, data=data, headers=dict(headers), method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as reply:
                return HttpResponse(status=reply.status, body=_decode(raw=reply.read()))
        except urllib.error.HTTPError as exc:
            return HttpResponse(status=exc.code, body=_decode(raw=exc.read()))
        except urllib.error.URLError as exc:
            msg = f"{method} {url} failed: {exc.reason}"
            raise SpaceKitError(msg) from exc


def _decode(*, raw: bytes) -> JsonValue:
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


class SpaceApi:
    """The public space and MCP endpoints, one method per call."""

    def __init__(self, *, credentials: Credentials, transport: Transport) -> None:
        self._credentials: Credentials = credentials
        self._transport: Transport = transport

    @property
    def target(self) -> str:
        return self._credentials.target.value

    def _headers(self) -> dict[str, str]:
        headers = {
            "x-user-id": self._credentials.user_id,
            "x-company-id": self._credentials.company_id,
            "x-api-version": API_VERSION,
            "Content-Type": "application/json",
        }
        if self._credentials.api_key:
            headers["Authorization"] = f"Bearer {self._credentials.api_key}"
        if self._credentials.app_id:
            headers["x-app-id"] = self._credentials.app_id
        return headers

    def _call(self, *, method: str, path: str, body: JsonValue = None) -> JsonValue:
        url = self._credentials.api_base.rstrip("/") + path
        reply = self._transport.request(
            method=method, url=url, headers=self._headers(), body=body
        )
        if reply.status >= 400:
            detail = json.dumps(reply.body)[:ERROR_BODY_CHARS]
            msg = f"{method} {path} failed with HTTP {reply.status}: {detail}"
            raise SpaceKitError(msg)
        return reply.body

    def get_space(self, *, space_id: str) -> JsonObject:
        body = self._call(method="GET", path=f"/space/{quote(space_id)}")
        return as_object(value=body, what=f"space {space_id}")

    def find_spaces_by_name(self, *, name: str) -> list[JsonObject]:
        query = urlencode({"name": name})
        body = as_object(
            value=self._call(method="GET", path=f"/space?{query}"),
            what="space list",
        )
        spaces = as_list(value=body.get("data"), what="space list data")
        return [
            space
            for space in spaces
            if isinstance(space, dict) and space.get("name") == name
        ]

    def create_space(self, *, payload: JsonObject) -> JsonObject:
        body = self._call(method="POST", path="/space", body=payload)
        return as_object(value=body, what="created space")

    def update_space(self, *, space_id: str, payload: JsonObject) -> JsonObject:
        body = self._call(
            method="PATCH", path=f"/space/{quote(space_id)}", body=payload
        )
        return as_object(value=body, what=f"updated space {space_id}")

    def delete_space(self, *, space_id: str) -> None:
        _ = self._call(method="DELETE", path=f"/space/{quote(space_id)}")

    def add_access(self, *, space_id: str, access: list[JsonValue]) -> JsonObject:
        body = self._call(
            method="POST",
            path=f"/space/{quote(space_id)}/access",
            body={"access": access},
        )
        return as_object(value=body, what=f"access of {space_id}")

    def list_mcp_servers(self) -> list[JsonObject]:
        body = as_object(
            value=self._call(method="GET", path="/mcp/servers"),
            what="MCP server list",
        )
        servers = as_list(value=body.get("mcpServers"), what="mcpServers")
        return [server for server in servers if isinstance(server, dict)]
