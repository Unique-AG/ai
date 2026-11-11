"""Integration tests against the LIVE CRM server over MCP-HTTP.

Skipped automatically if the server isn't running on :8004.
"""

import asyncio
import json
import urllib.request

import pytest

pytestmark = pytest.mark.integration

URL = "http://localhost:8004/mcp"


def _server_up() -> bool:
    try:
        urllib.request.urlopen("http://localhost:8004/", timeout=2)
        return True
    except Exception:
        return False


if not _server_up():  # pragma: no cover
    pytest.skip("crm server not running on :8004", allow_module_level=True)

from fastmcp import Client  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


async def _names():
    async with Client(URL) as c:
        return [t.name for t in await c.list_tools()]


async def _call(name, args):
    async with Client(URL) as c:
        res = await c.call_tool(name, args)
        return json.loads(res.content[0].text)


def test_tool_inventory():
    names = _run(_names())
    assert len(names) == 22
    assert "Reset_Demo_Data" in names
    assert {"get_party_identity", "list_clients", "get_talking_points", "get_meetings",
            "edit_dashboard_section", "screen_person"} <= set(names)


def test_party_identity_over_http():
    r = _run(_call("get_party_identity", {"input": "Brunner"}))
    assert r["client_id"] == "PTY-0002005"


def test_memory_crud_over_http():
    # Markus is seeded at positions 1-5; use a free slot within the MEMORY_MAX_POINTS cap.
    _run(_call("upsert_talking_point", {"client_id": "Markus", "position": 18, "text": "http test"}))
    rows = _run(_call("get_talking_points", {"client_id": "Markus"}))
    assert any(r["position"] == 18 for r in rows)
    _run(_call("delete_talking_point", {"client_id": "Markus", "position": 18}))
    rows2 = _run(_call("get_talking_points", {"client_id": "Markus"}))
    assert not any(r["position"] == 18 for r in rows2)


def test_unknown_client_over_http():
    r = _run(_call("get_relationship", {"input": "Nope"}))
    assert "Unknown client" in r["error"]
