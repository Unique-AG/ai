"""Citation rows from list results, typed blocks, and untitled output."""

from __future__ import annotations

import json
from pathlib import Path

from unique_sdk.cli.commands.mcp import record_mcp_citations

_PAGE_ONE_URL = "https://example.com/docs/auth"
_PAGE_TWO_URL = "https://example.com/docs/tokens"

_LIST_PAYLOAD = {
    "success": True,
    "results": [
        {
            "id": "AAA111",
            "title": "Auth overview",
            "webUrl": _PAGE_ONE_URL,
            "text": "How sign-in works.",
        },
        {
            "id": "BBB222",
            "title": "Token refresh",
            "webUrl": _PAGE_TWO_URL,
            "text": "When to refresh a token.",
        },
    ],
}


class _FakeMCPResponse:
    """Stand-in for a unique_sdk.MCP response (attribute access)."""

    def __init__(self, content: list, *, mcp_server_id: str | None = None) -> None:
        self.content = content
        self.isError = False
        self.mcpServerId = mcp_server_id


class _TypedTextBlock:
    """A content block that is not a dict.

    Mirrors ``mcp.types.TextContent``.
    """

    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


def _refs(unique_dir: Path) -> list[dict]:
    path = unique_dir / "mcp-refs.jsonl"
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _record(response: _FakeMCPResponse, unique_dir: Path) -> str | None:
    return record_mcp_citations(
        response,
        tool_name="search_pages",
        server_name="docs",
        unique_dir=unique_dir,
        formatted_text=json.dumps(_LIST_PAYLOAD),
    )


def test_dict_blocks_yield_one_row_per_item(tmp_path: Path) -> None:
    unique_dir = tmp_path / ".unique"
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": json.dumps(_LIST_PAYLOAD)}],
        mcp_server_id="docs",
    )

    _record(response, unique_dir)

    titles = [row["title"] for row in _refs(unique_dir)]
    assert titles == ["Auth overview", "Token refresh"]


def test_typed_content_blocks_yield_one_row_per_item(tmp_path: Path) -> None:
    unique_dir = tmp_path / ".unique"
    response = _FakeMCPResponse(
        content=[_TypedTextBlock(json.dumps(_LIST_PAYLOAD))],
        mcp_server_id="docs",
    )

    _record(response, unique_dir)

    titles = [row["title"] for row in _refs(unique_dir)]
    assert titles == ["Auth overview", "Token refresh"]


def test_recorded_row_carries_per_item_url(tmp_path: Path) -> None:
    unique_dir = tmp_path / ".unique"
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": json.dumps(_LIST_PAYLOAD)}],
        mcp_server_id="docs",
    )

    _record(response, unique_dir)

    urls = [row.get("url") for row in _refs(unique_dir)]
    assert urls == [_PAGE_ONE_URL, _PAGE_TWO_URL]


def test_markdown_title_url_list_yields_one_row_per_page(tmp_path: Path) -> None:
    unique_dir = tmp_path / ".unique"
    body = (
        "- Auth overview\n"
        "  https://example.com/docs/auth\n"
        "- Token refresh\n"
        "  https://example.com/docs/tokens\n"
    )
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    record_mcp_citations(
        response,
        tool_name="search_pages",
        server_name="docs",
        unique_dir=unique_dir,
        formatted_text=body,
    )
    rows = _refs(unique_dir)
    assert [(row["title"], row.get("url")) for row in rows] == [
        ("Auth overview", "https://example.com/docs/auth"),
        ("Token refresh", "https://example.com/docs/tokens"),
    ]


def test_titleless_row_is_labelled_with_the_tool_name(tmp_path: Path) -> None:
    unique_dir = tmp_path / ".unique"
    response = _FakeMCPResponse(content=[{"type": "text", "text": "status: ok"}])

    footer = record_mcp_citations(
        response,
        tool_name="search_pages",
        server_name="docs",
        unique_dir=unique_dir,
        formatted_text="status: ok",
    )

    assert "[mcpsource1] search_pages" in (footer or "")
    rows = _refs(unique_dir)
    assert rows[0]["title"] is None
    assert rows[0]["text"] == "status: ok"
