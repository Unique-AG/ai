"""Tests for the ``unique-cli mcp`` command.

Covers the per-turn output manifest used to ground the hallucination check
(UN-21951) and the per-turn refs manifest used for MCP citations (UN-21285).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import unique_sdk
from unique_sdk.cli.commands import mcp as mcp_cmd
from unique_sdk.cli.commands.mcp import cmd_mcp
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState

_OUTPUT_MANIFEST = Path(".unique") / "mcp-output.jsonl"
_REFS_MANIFEST = Path(".unique") / "mcp-refs.jsonl"


class _FakeMCPResponse:
    """Stand-in for a unique_sdk.MCP response (attribute access)."""

    def __init__(
        self,
        content: list[dict] | None = None,
        *,
        is_error: bool = False,
        mcp_server_id: str | None = None,
        name: str | None = None,
    ) -> None:
        self.content = content or []
        self.isError = is_error
        self.mcpServerId = mcp_server_id
        self.name = name


def _config() -> Config:
    return Config(
        user_id="u1",
        company_id="c1",
        api_key="key",
        app_id="app",
        api_base="https://example.com",
    )


def _state() -> ShellState:
    return ShellState(_config())


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


def _lines(tmp_path: Path, manifest: Path) -> list[dict]:
    path = tmp_path / manifest
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _run(
    name: str,
    response: _FakeMCPResponse,
    formatted: str = "result",
    arguments: dict | None = None,
) -> str:
    payload = json.dumps({"name": name, "arguments": arguments or {}})
    with (
        patch.object(unique_sdk.MCP, "call_tool", return_value=response),
        patch.object(mcp_cmd, "format_mcp_response", return_value=formatted),
    ):
        return cmd_mcp(_state(), "chat_1", "msg_1", payload=payload)


# ── Output manifest (UN-21951) ───────────────────────────────────────────────


def test_cmd_mcp_writes_output_manifest(tmp_path: Path) -> None:
    out = _run(
        "mcp__crm__get_account",
        _FakeMCPResponse(),
        formatted="ACME revenue: 1M",
    )
    assert out.startswith("ACME revenue: 1M")
    entries = _lines(tmp_path, _OUTPUT_MANIFEST)
    assert entries[0]["toolName"] == "mcp__crm__get_account"
    assert entries[0]["serverName"] == "crm"
    assert entries[0]["text"] == "ACME revenue: 1M"


def test_cmd_mcp_truncates_large_output(tmp_path: Path) -> None:
    big = "x" * (mcp_cmd._MCP_OUTPUT_TEXT_CHAR_LIMIT + 500)
    _run("mcp__kb__search", _FakeMCPResponse(), formatted=big)
    text = _lines(tmp_path, _OUTPUT_MANIFEST)[0]["text"]
    assert len(text) == mcp_cmd._MCP_OUTPUT_TEXT_CHAR_LIMIT


# ── Refs manifest / citations (UN-21285) ─────────────────────────────────────
#
# One source per retrieved item — a *title* describing what was retrieved (no
# URL). Titles come from resource_link names or a JSON-title heuristic; falls
# back to a title-less tool chip when the result has no recognizable title.


def test_resource_link_item_has_title_no_url(tmp_path: Path) -> None:
    response = _FakeMCPResponse(
        content=[
            {
                "type": "resource_link",
                "uri": "https://kb.example.com/doc/9",
                "name": "RAG Retrieval Baseline",
                "description": "Why retrieval fails",
            }
        ]
    )
    out = _run("mcp__kb__fetch", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert refs == [
        {
            "sourceNumber": 1,
            "toolName": "mcp__kb__fetch",
            "serverName": "kb",
            "title": "RAG Retrieval Baseline",
            "snippet": "Why retrieval fails",
        }
    ]
    assert "[mcpsource1] RAG Retrieval Baseline" in out
    assert "https://" not in out.split("result", 1)[1]  # no URL leaked into footer


def test_json_in_text_yields_title_no_url(tmp_path: Path) -> None:
    # Atlassian-style: a JSON record in a text block → title only.
    body = json.dumps(
        {"title": "RAG Retrieval Baseline", "webUrl": "https://confluence/x/2295"}
    )
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    _run("mcp__atlassian__getConfluencePage", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert refs[0]["title"] == "RAG Retrieval Baseline"
    assert "url" not in refs[0]


def test_multiple_items_get_distinct_numbers(tmp_path: Path) -> None:
    response = _FakeMCPResponse(
        content=[
            {"type": "resource_link", "uri": "https://e/a", "name": "Doc A"},
            {"type": "resource_link", "uri": "https://e/b", "name": "Doc B"},
        ]
    )
    _run("mcp__kb__search", response)
    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert {r["title"]: r["sourceNumber"] for r in refs} == {"Doc A": 1, "Doc B": 2}


def test_same_title_dedupes_across_calls(tmp_path: Path) -> None:
    r = _FakeMCPResponse(
        content=[{"type": "resource_link", "uri": "https://e/a", "name": "Doc A"}]
    )
    _run("mcp__kb__fetch", r)
    _run("mcp__kb__fetch", r)  # same title → reuse source 1
    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert len(refs) == 1
    assert refs[0]["sourceNumber"] == 1


def test_titleless_result_falls_back_to_tool_chip(tmp_path: Path) -> None:
    # No resource blocks, no JSON title → one title-less chip (runner names it
    # after the tool). No URL is recorded.
    response = _FakeMCPResponse(content=[{"type": "text", "text": "status: ok"}])
    _run("mcp__crm__update", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert refs[0]["title"] is None
    assert "url" not in refs[0]


def test_server_name_falls_back_to_mcp_server_id(tmp_path: Path) -> None:
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": "ok"}],
        mcp_server_id="srv_42",
    )
    _run("plainTool", response)
    assert _lines(tmp_path, _REFS_MANIFEST)[0]["serverName"] == "srv_42"


def test_refs_manifest_failure_does_not_break_tool_call(tmp_path: Path) -> None:
    response = _FakeMCPResponse(content=[{"type": "text", "text": "x"}])
    payload = json.dumps({"name": "mcp__crm__get", "arguments": {}})
    with (
        patch.object(unique_sdk.MCP, "call_tool", return_value=response),
        patch.object(mcp_cmd, "format_mcp_response", return_value="result text"),
        patch.object(
            mcp_cmd, "_append_turn_refs_manifest_entry", side_effect=OSError("full")
        ),
    ):
        out = cmd_mcp(_state(), "chat_1", "msg_1", payload=payload)

    # Tool result still returned; just no citation footer.
    assert out.startswith("result text")


def test_api_error_writes_no_manifest(tmp_path: Path) -> None:
    payload = json.dumps({"name": "mcp__crm__get", "arguments": {}})
    with patch.object(
        unique_sdk.MCP, "call_tool", side_effect=unique_sdk.APIError("boom")
    ):
        out = cmd_mcp(_state(), "chat_1", "msg_1", payload=payload)

    assert out.startswith("mcp:")
    assert _lines(tmp_path, _REFS_MANIFEST) == []
    assert _lines(tmp_path, _OUTPUT_MANIFEST) == []
