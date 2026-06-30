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
from unique_sdk.cli.commands.mcp import cmd_mcp, record_mcp_citations
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
            "details": None,
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


# ── Reference enrichment / details line (UN-22310) ───────────────────────────


def test_json_in_text_extracts_details_date_and_author(tmp_path: Path) -> None:
    # Atlassian-style record carrying a date + a nested author object.
    body = json.dumps(
        {
            "title": "Unique <> JP Morgan Introduction Meeting",
            "updated": "10/10/2026",
            "author": {"displayName": "Jamie Dimon"},
        }
    )
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    _run("mcp__atlassian__getConfluencePage", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert refs[0]["title"] == "Unique <> JP Morgan Introduction Meeting"
    assert refs[0]["details"] == "10/10/2026 - Jamie Dimon"


def test_json_in_text_details_author_only(tmp_path: Path) -> None:
    body = json.dumps({"title": "Some email", "creator": "Jane Roe"})
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    _run("mcp__mail__get", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert refs[0]["details"] == "Jane Roe"


def test_json_in_text_no_details_when_absent(tmp_path: Path) -> None:
    body = json.dumps({"title": "Some email"})
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    _run("mcp__mail__get", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert refs[0]["details"] is None


def test_resource_link_item_has_no_details(tmp_path: Path) -> None:
    # resource_link blocks carry no date/author → details omitted (None).
    response = _FakeMCPResponse(
        content=[{"type": "resource_link", "uri": "https://e/a", "name": "Doc A"}]
    )
    _run("mcp__kb__fetch", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert refs[0]["details"] is None


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


def test_dedup_backfills_details_from_later_call(tmp_path: Path) -> None:
    # First call retrieves "Doc A" as a bare resource_link (no date/author) →
    # source 1 with no details. A later call returns the same titled record as
    # JSON carrying a date + author. The dedup reuses source 1, and the newly
    # extracted details must be backfilled onto the existing entry (the runner
    # reads one entry per source number, so an empty details would otherwise
    # stick for the whole turn).
    first = _FakeMCPResponse(
        content=[{"type": "resource_link", "uri": "https://e/a", "name": "Doc A"}]
    )
    _run("mcp__kb__fetch", first)
    assert _lines(tmp_path, _REFS_MANIFEST)[0]["details"] is None

    enriched_body = json.dumps(
        {
            "title": "Doc A",
            "updated": "10/10/2026",
            "author": {"displayName": "Jamie Dimon"},
        }
    )
    second = _FakeMCPResponse(content=[{"type": "text", "text": enriched_body}])
    _run("mcp__kb__fetch", second)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert len(refs) == 1  # still deduped — one entry, one source number
    assert refs[0]["sourceNumber"] == 1
    assert refs[0]["details"] == "10/10/2026 - Jamie Dimon"


def test_dedup_does_not_clobber_existing_details(tmp_path: Path) -> None:
    # First call already has details; a later detail-less call must not erase
    # them (backfill only fills an empty details, never overwrites).
    enriched_body = json.dumps({"title": "Doc A", "updated": "01/01/2026"})
    first = _FakeMCPResponse(content=[{"type": "text", "text": enriched_body}])
    _run("mcp__kb__fetch", first)

    bare = _FakeMCPResponse(
        content=[{"type": "resource_link", "uri": "https://e/a", "name": "Doc A"}]
    )
    _run("mcp__kb__fetch", bare)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert len(refs) == 1
    assert refs[0]["details"] == "01/01/2026"


def test_different_tools_same_title_get_distinct_numbers(tmp_path: Path) -> None:
    # Tool A records "Doc A" as source 1.
    r = _FakeMCPResponse(
        content=[{"type": "resource_link", "uri": "https://e/a", "name": "Doc A"}]
    )
    _run("mcp__kb__fetch", r)
    # Tool B retrieves the same-named doc → different tool → must get source 2,
    # not reuse source 1 (the bug: prior code used the *current* tool_name when
    # rebuilding numbers_by_key, making Tool B collide with Tool A's entry).
    _run("mcp__crm__get", r)
    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert len(refs) == 2
    numbers = {row["toolName"]: row["sourceNumber"] for row in refs}
    assert numbers["mcp__kb__fetch"] == 1
    assert numbers["mcp__crm__get"] == 2


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


def test_output_manifest_gets_server_id_from_response(tmp_path: Path) -> None:
    # Bare skill-mode tool names have no mcp__ prefix, so _server_name_from_tool
    # returns None. The output manifest must still record serverName via the
    # response's mcpServerId — same logic as the refs manifest.
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": "status: ok"}],
        mcp_server_id="srv_99",
    )
    _run("plainTool", response, formatted="ok text")
    entries = _lines(tmp_path, _OUTPUT_MANIFEST)
    assert entries[0]["serverName"] == "srv_99"


def test_partial_refs_returned_when_later_write_fails(tmp_path: Path) -> None:
    # When writing the refs manifest entry for a later item fails, items already
    # successfully written must still appear in the citation footer.
    from unique_sdk.cli.commands.mcp import _annotate_mcp_results_for_citations

    response = _FakeMCPResponse(
        content=[
            {"type": "resource_link", "uri": "https://e/a", "name": "Doc A"},
            {"type": "resource_link", "uri": "https://e/b", "name": "Doc B"},
        ]
    )

    refs_path = tmp_path / ".unique" / "mcp-refs.jsonl"
    refs_path.parent.mkdir(parents=True, exist_ok=True)

    write_count = [0]
    original_append = mcp_cmd._append_turn_refs_manifest_entry

    def fail_second_write(path, entry):
        write_count[0] += 1
        if write_count[0] == 2:
            raise OSError("disk full")
        original_append(path, entry)

    with patch.object(
        mcp_cmd, "_append_turn_refs_manifest_entry", side_effect=fail_second_write
    ):
        annotated = _annotate_mcp_results_for_citations(
            response,
            tool_name="mcp__kb__search",
            server_name="kb",
            refs_log_path=refs_path,
        )

    # First item was written and annotated; second was not.
    assert len(annotated) == 1
    assert annotated[0][0] == 1
    assert annotated[0][1]["title"] == "Doc A"


def test_rewrite_failure_preserves_live_manifest(tmp_path: Path) -> None:
    # A failed/partial rewrite must never truncate the live manifest: the new
    # content goes to a temp file that is os.replace-d into place only on
    # success, so a mid-write error leaves the original intact and no temp file
    # behind.
    from unique_sdk.cli.commands._citation_manifest import (
        _append_turn_refs_manifest_entry,
        _rewrite_turn_refs_manifest,
    )

    refs_path = tmp_path / ".unique" / "mcp-refs.jsonl"
    original = {"sourceNumber": 1, "toolName": "mcp__kb__fetch", "title": "Doc A"}
    _append_turn_refs_manifest_entry(refs_path, original)

    with patch(
        "unique_sdk.cli.commands._citation_manifest.json.dumps",
        side_effect=OSError("disk full"),
    ):
        with pytest.raises(OSError):
            _rewrite_turn_refs_manifest(
                refs_path, [{**original, "details": "10/10/2026"}]
            )

    # Original content survives; no leftover temp file in the directory.
    assert _lines(tmp_path, _REFS_MANIFEST) == [original]
    assert list(refs_path.parent.glob("*.tmp")) == []


def test_rewrite_succeeds_despite_stale_temp_file(tmp_path: Path) -> None:
    # A leftover temp file from an earlier crashed rewrite must not block the
    # next one: each call uses a fresh unique temp name (mkstemp), so it cannot
    # collide with stale debris.
    from unique_sdk.cli.commands._citation_manifest import (
        _append_turn_refs_manifest_entry,
        _rewrite_turn_refs_manifest,
    )

    refs_path = tmp_path / ".unique" / "mcp-refs.jsonl"
    original = {"sourceNumber": 1, "toolName": "mcp__kb__fetch", "title": "Doc A"}
    _append_turn_refs_manifest_entry(refs_path, original)

    # Simulate debris from a prior process that died mid-rewrite.
    (refs_path.parent / "mcp-refs.jsonl.12345.tmp").write_text("garbage")

    updated = {**original, "details": "10/10/2026"}
    _rewrite_turn_refs_manifest(refs_path, [updated])

    assert _lines(tmp_path, _REFS_MANIFEST) == [updated]


def test_api_error_writes_no_manifest(tmp_path: Path) -> None:
    payload = json.dumps({"name": "mcp__crm__get", "arguments": {}})
    with patch.object(
        unique_sdk.MCP, "call_tool", side_effect=unique_sdk.APIError("boom")
    ):
        out = cmd_mcp(_state(), "chat_1", "msg_1", payload=payload)

    assert out.startswith("mcp:")
    assert _lines(tmp_path, _REFS_MANIFEST) == []
    assert _lines(tmp_path, _OUTPUT_MANIFEST) == []


# ── record_mcp_citations: shared helper (skills + tools-mode proxy) ───────────
#
# The CLI flow defaults to ``Path.cwd()/.unique`` (covered above via cmd_mcp);
# these exercise the explicit ``unique_dir`` path the in-process tools-mode proxy
# uses, where cwd is NOT the agent workspace.


def _unique_lines(unique_dir: Path, filename: str) -> list[dict]:
    path = unique_dir / filename
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_record_mcp_citations_writes_both_manifests_under_unique_dir(
    tmp_path: Path,
) -> None:
    unique_dir = tmp_path / "ws" / ".unique"
    response = _FakeMCPResponse(
        content=[
            {
                "type": "resource_link",
                "uri": "https://kb.example.com/doc/9",
                "name": "RAG Retrieval Baseline",
                "description": "Why retrieval fails",
            }
        ],
        mcp_server_id="kb",
    )

    footer = record_mcp_citations(
        response,
        tool_name="fetch",  # bare advertised name (tools mode)
        server_name="kb",
        unique_dir=unique_dir,
        formatted_text="Why retrieval fails — details here",
    )

    # No `.unique/.unique/` nesting — filenames join directly onto unique_dir.
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    output = _unique_lines(unique_dir, "mcp-output.jsonl")
    assert refs == [
        {
            "sourceNumber": 1,
            "toolName": "fetch",
            "serverName": "kb",
            "title": "RAG Retrieval Baseline",
            "snippet": "Why retrieval fails",
            "details": None,
        }
    ]
    assert output == [
        {
            "toolName": "fetch",
            "serverName": "kb",
            "text": "Why retrieval fails — details here",
        }
    ]
    assert "[mcpsource1] RAG Retrieval Baseline" in footer


def test_record_mcp_citations_dedups_title_across_calls(tmp_path: Path) -> None:
    unique_dir = tmp_path / ".unique"

    def _resp() -> _FakeMCPResponse:
        return _FakeMCPResponse(
            content=[{"type": "resource_link", "uri": "x", "name": "Same Doc"}],
            mcp_server_id="kb",
        )

    f1 = record_mcp_citations(
        _resp(),
        tool_name="fetch",
        server_name="kb",
        unique_dir=unique_dir,
        formatted_text="first",
    )
    f2 = record_mcp_citations(
        _resp(),
        tool_name="fetch",
        server_name="kb",
        unique_dir=unique_dir,
        formatted_text="second",
    )

    # Same title → one refs entry / one reused source number; both calls'
    # output is grounded (no dedup on the output manifest).
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    output = _unique_lines(unique_dir, "mcp-output.jsonl")
    assert len(refs) == 1
    assert refs[0]["sourceNumber"] == 1
    assert "[mcpsource1] Same Doc" in f1
    assert "[mcpsource1] Same Doc" in f2
    assert [e["text"] for e in output] == ["first", "second"]


def test_record_mcp_citations_concurrent_monotonic_numbers(
    tmp_path: Path,
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    unique_dir = tmp_path / ".unique"
    n = 8

    def _record(i: int) -> str:
        response = _FakeMCPResponse(
            content=[{"type": "resource_link", "uri": f"u{i}", "name": f"Doc {i}"}],
            mcp_server_id="kb",
        )
        return record_mcp_citations(
            response,
            tool_name="fetch",
            server_name="kb",
            unique_dir=unique_dir,
            formatted_text=f"body {i}",
        )

    with ThreadPoolExecutor(max_workers=n) as pool:
        list(pool.map(_record, range(n)))

    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    numbers = sorted(e["sourceNumber"] for e in refs)
    # Distinct titles → one entry each, with unique consecutive numbers and no
    # collisions despite concurrent writers (the per-turn flock serializes them).
    assert numbers == list(range(1, n + 1))
    assert len(_unique_lines(unique_dir, "mcp-output.jsonl")) == n
