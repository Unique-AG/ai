"""Integration tests against the LIVE Advisory server over MCP-HTTP.

Skipped automatically if the server isn't running on :8003. Run with the server up:
    uv run python src/mcp_advisory/mcp_advisory.py    # in another shell
    uv run pytest -m integration
"""

import asyncio
import json
import urllib.request

import pytest

pytestmark = pytest.mark.integration

URL = "http://localhost:8003/mcp"


def _server_up() -> bool:
    try:
        urllib.request.urlopen("http://localhost:8003/", timeout=2)
        return True
    except Exception:
        return False


if not _server_up():  # pragma: no cover
    pytest.skip("advisory server not running on :8003", allow_module_level=True)

from fastmcp import Client  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


async def _tool_names():
    async with Client(URL) as c:
        return [t.name for t in await c.list_tools()]


async def _call(name, args):
    async with Client(URL) as c:
        res = await c.call_tool(name, args)
        return json.loads(res.content[0].text)


def test_tool_inventory():
    names = _run(_tool_names())
    assert len(names) == 18
    assert "Reset_Demo_Data" in names
    assert {"get_holdings", "get_house_view", "recommend_model", "get_coverage_scenario"} <= set(names)


def test_holdings_over_http():
    r = _run(_call("get_holdings", {"input": "Markus"}))
    assert r["client_id"] == "CH-PB-0049217" and len(r["positions"]) > 0


def test_house_view_over_http():
    r = _run(_call("get_house_view", {}))
    assert len(r["views"]) >= 5


def test_unknown_client_over_http():
    r = _run(_call("get_performance", {"input": "Nope"}))
    assert "Unknown client" in r["error"]
