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
_REFS_SEED = Path(".unique") / "mcp-refs-seed.json"


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
    # Sources block leads so markers survive harness-side spilling of large
    # results (UN-22309); the formatted tool output follows it.
    assert out.startswith("Sources — MANDATORY")
    assert "ACME revenue: 1M" in out
    assert out.index("Sources — MANDATORY") < out.index("ACME revenue: 1M")
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
# URL). Titles come from (in order) a per-tool ``reference_mapping``, then
# resource_link names, then a JSON-title heuristic over text blocks — the
# heuristic tolerates a non-JSON preamble and unwraps a container key
# (``{"issues": [...]}``) so each record becomes its own reference; falls back
# to a title-less tool chip when the result has no recognizable title.


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
            "text": "Why retrieval fails",
        }
    ]
    assert "[mcpsource1] RAG Retrieval Baseline" in out
    assert "https://" not in out  # no URL leaked into the Sources block or body


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


def test_json_in_text_unwraps_wrapped_array_into_items(tmp_path: Path) -> None:
    # Atlassian JQL search: records wrapped under an "issues" key must each
    # become their own reference (via the top-level "key"), not collapse into
    # one title-less tool chip.
    body = json.dumps(
        {
            "issues": [
                {"key": "UN-1", "fields": {"summary": "First"}},
                {"key": "UN-2", "fields": {"summary": "Second"}},
            ]
        }
    )
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    _run("mcp__atlassian__searchJiraIssuesUsingJql", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert {r["title"]: r["sourceNumber"] for r in refs} == {"UN-1": 1, "UN-2": 2}


def test_json_in_text_tolerates_non_json_preamble(tmp_path: Path) -> None:
    # Some servers (Atlassian) prefix a human-readable notice before the JSON;
    # the whole string is not valid JSON, so the embedded body must be located.
    body = json.dumps({"issues": [{"key": "UN-9", "fields": {"summary": "X"}}]})
    text = f"[IMPORTANT: notice with a [bracket] inside]\n{body}"
    response = _FakeMCPResponse(content=[{"type": "text", "text": text}])
    _run("mcp__atlassian__searchJiraIssuesUsingJql", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert [r["title"] for r in refs] == ["UN-9"]


def test_json_in_text_object_with_dict_container_key_stays_untitled(
    tmp_path: Path,
) -> None:
    # A container key whose value is a dict (not a list) must NOT be unwrapped;
    # with no top-level title the result falls back to a single tool chip.
    body = json.dumps({"data": {"users": {"users": []}}})
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    _run("mcp__atlassian__lookupJiraAccountId", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert refs == [
        {
            "sourceNumber": 1,
            "toolName": "mcp__atlassian__lookupJiraAccountId",
            "serverName": "atlassian",
            "title": None,
            "snippet": None,
            "details": None,
            # Title-less fallback grounds on the whole formatted output
            # (`_run` formats every response as "result").
            "text": "result",
        }
    ]


def test_json_in_text_titled_record_not_split_by_content_key(tmp_path: Path) -> None:
    # A single page/document payload that carries its own top-level title plus a
    # ``content`` body (an ambiguous container key) must keep the page title
    # rather than being split into title-less inner blocks.
    body = json.dumps(
        {
            "title": "Retrieval Design Doc",
            "content": [{"block": "intro"}, {"block": "body"}],
        }
    )
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    _run("mcp__atlassian__getConfluencePage", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert [r["title"] for r in refs] == ["Retrieval Design Doc"]


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


# ── Per-item text ground truth (UN-22762) ────────────────────────────────────
#
# Each refs-manifest entry records the cited item's underlying ``text`` so the
# runner's hallucination check grounds every ``[mcpsourceN]`` on what was
# actually retrieved, instead of only the head-truncated flat output manifest.


def test_json_in_text_records_serialized_record_as_text(tmp_path: Path) -> None:
    # JSON-title heuristic: each record's text is the serialized record — the
    # titled field plus all metadata the agent may cite.
    record = {"key": "UN-1", "fields": {"summary": "First"}}
    body = json.dumps({"issues": [record]})
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    _run("mcp__atlassian__searchJiraIssuesUsingJql", response)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert json.loads(refs[0]["text"]) == record


def test_reference_mapping_record_text_is_serialized_record(tmp_path: Path) -> None:
    unique_dir = tmp_path / ".unique"
    record = {"key": "UN-7", "fields": {"summary": "Deep"}, "status": "Done"}
    body = json.dumps({"issues": [record]})
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    record_mcp_citations(
        response,
        tool_name="searchJiraIssuesUsingJql",
        server_name="atlassian",
        unique_dir=unique_dir,
        formatted_text=body,
        reference_mapping={"listPath": "issues", "titlePath": "key"},
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert json.loads(refs[0]["text"]) == record


def test_reference_mapping_plain_string_record_text_is_the_string(
    tmp_path: Path,
) -> None:
    unique_dir = tmp_path / ".unique"
    doc = "# Alpha Guide\nbody with the cited fact"
    body = json.dumps({"docs": [doc]})
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    record_mcp_citations(
        response,
        tool_name="list_docs",
        server_name="docs",
        unique_dir=unique_dir,
        formatted_text=body,
        reference_mapping={"listPath": "docs", "titleFromText": True},
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert refs[0]["text"] == doc


def test_reference_mapping_text_doc_records_full_text(tmp_path: Path) -> None:
    # titleFromText on a fetched Markdown doc: the chip's text is the whole
    # document body, not just the heading line used for the title.
    unique_dir = tmp_path / ".unique"
    doc = "# Retrieval Evaluation\n\n" + "Deep fact far into the document. " * 50
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": doc}], mcp_server_id="docs"
    )
    record_mcp_citations(
        response,
        tool_name="read_doc",
        server_name="docs",
        unique_dir=unique_dir,
        formatted_text=doc,
        reference_mapping={"titleFromText": True},
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert refs[0]["text"] == doc


def test_titleless_fallback_records_formatted_text(tmp_path: Path) -> None:
    # The title-less tool chip grounds on the whole formatted output the agent
    # saw, so citing it still reaches the hallucination check with real text.
    unique_dir = tmp_path / ".unique"
    response = _FakeMCPResponse(content=[{"type": "text", "text": "status: ok"}])
    record_mcp_citations(
        response,
        tool_name="update",
        server_name="crm",
        unique_dir=unique_dir,
        formatted_text="status: ok — record 42 updated",
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert refs[0]["title"] is None
    assert refs[0]["text"] == "status: ok — record 42 updated"


def test_resource_link_text_is_none_when_no_description(tmp_path: Path) -> None:
    response = _FakeMCPResponse(
        content=[{"type": "resource_link", "uri": "https://e/a", "name": "Doc A"}]
    )
    _run("mcp__kb__fetch", response)
    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert refs[0]["text"] is None


def test_ref_text_truncated_to_writer_cap(tmp_path: Path) -> None:
    unique_dir = tmp_path / ".unique"
    doc = "# Big Doc\n" + "x" * (mcp_cmd._MCP_REF_TEXT_CHAR_LIMIT + 500)
    response = _FakeMCPResponse(content=[{"type": "text", "text": doc}])
    record_mcp_citations(
        response,
        tool_name="read_doc",
        server_name="docs",
        unique_dir=unique_dir,
        formatted_text=doc,
        reference_mapping={"titleFromText": True},
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert len(refs[0]["text"]) == mcp_cmd._MCP_REF_TEXT_CHAR_LIMIT


def test_dedup_backfills_longer_text_from_later_call(tmp_path: Path) -> None:
    # Search first (small serialized record), then a full fetch of the same
    # titled item: the dedup reuses source 1 and upgrades its text to the
    # longer capture — the richer ground truth for the hallucination check.
    search_body = json.dumps({"results": [{"title": "Doc A"}]})
    first = _FakeMCPResponse(content=[{"type": "text", "text": search_body}])
    _run("mcp__kb__search", first, formatted=search_body)
    short_text = _lines(tmp_path, _REFS_MANIFEST)[0]["text"]

    full_record = {"title": "Doc A", "body": "Full page body. " * 100}
    second = _FakeMCPResponse(
        content=[{"type": "text", "text": json.dumps(full_record)}]
    )
    _run("mcp__kb__search", second, formatted=json.dumps(full_record))

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert len(refs) == 1  # still deduped — one entry, one source number
    assert refs[0]["sourceNumber"] == 1
    assert len(refs[0]["text"]) > len(short_text)
    assert json.loads(refs[0]["text"]) == full_record


def test_dedup_keeps_longer_existing_text(tmp_path: Path) -> None:
    # A later, poorer capture of the same item must not downgrade the stored
    # text (prefer-longer, never clobber with shorter).
    full_record = {"title": "Doc A", "body": "Full page body. " * 100}
    first = _FakeMCPResponse(
        content=[{"type": "text", "text": json.dumps(full_record)}]
    )
    _run("mcp__kb__search", first, formatted=json.dumps(full_record))

    second = _FakeMCPResponse(
        content=[{"type": "text", "text": json.dumps({"title": "Doc A"})}]
    )
    _run("mcp__kb__search", second)

    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert len(refs) == 1
    assert json.loads(refs[0]["text"]) == full_record


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
            "text": "Why retrieval fails",
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


# ── Chat-monotonic source numbering / seed file (UN-23199) ───────────────────
#
# The SI runner wipes ``mcp-refs.jsonl`` between turns, so manifest-derived
# numbering would restart at 1 each turn. A persistent sibling seed file
# (``mcp-refs-seed.json``) records the highest source number ever assigned in
# the chat so numbering stays monotonic across the runner's per-turn reset.


def test_seed_continues_numbering_after_manifest_wiped(tmp_path: Path) -> None:
    # Turn 1: two items → sources 1, 2. The seed file records the max.
    r1 = _FakeMCPResponse(
        content=[
            {"type": "resource_link", "uri": "https://e/a", "name": "Doc A"},
            {"type": "resource_link", "uri": "https://e/b", "name": "Doc B"},
        ]
    )
    _run("mcp__kb__search", r1)
    first_max = max(r["sourceNumber"] for r in _lines(tmp_path, _REFS_MANIFEST))
    assert first_max == 2

    # Seed file exists with the contract body; manifest is wiped (runner reset).
    seed_path = tmp_path / _REFS_SEED
    assert seed_path.is_file()
    assert json.loads(seed_path.read_text(encoding="utf-8")) == {"maxSourceNumber": 2}
    (tmp_path / _REFS_MANIFEST).unlink()

    # Turn 2: a fresh item must continue above the prior max, not restart at 1.
    r2 = _FakeMCPResponse(
        content=[{"type": "resource_link", "uri": "https://e/c", "name": "Doc C"}]
    )
    _run("mcp__kb__search", r2)
    refs2 = _lines(tmp_path, _REFS_MANIFEST)
    assert [r["sourceNumber"] for r in refs2] == [first_max + 1]
    assert refs2[0]["title"] == "Doc C"
    assert json.loads(seed_path.read_text(encoding="utf-8")) == {"maxSourceNumber": 3}


def test_absent_seed_reproduces_pre_seed_numbering(tmp_path: Path) -> None:
    # No seed file → seed 0 → numbering identical to today's behavior (starts 1).
    response = _FakeMCPResponse(
        content=[{"type": "resource_link", "uri": "https://e/a", "name": "Doc A"}]
    )
    _run("mcp__kb__fetch", response)
    assert _lines(tmp_path, _REFS_MANIFEST)[0]["sourceNumber"] == 1


def test_write_seed_refuses_symlinked_temp_path(tmp_path: Path) -> None:
    # Bugbot security regression: the seed write must not follow a symlink
    # pre-planted at the predictable temp path, so it cannot be redirected to
    # overwrite a file outside the refs directory.
    unique_dir = tmp_path / ".unique"
    unique_dir.mkdir()
    seed_path = unique_dir / "mcp-refs-seed.json"
    outside = tmp_path / "outside.txt"
    outside.write_text("SECRET", encoding="utf-8")
    (unique_dir / "mcp-refs-seed.json.tmp").symlink_to(outside)

    # Best-effort: the O_NOFOLLOW open fails and is swallowed (no raise).
    mcp_cmd._write_mcp_refs_seed(seed_path, 5)

    # The symlink target outside the refs dir is untouched, and no seed landed.
    assert outside.read_text(encoding="utf-8") == "SECRET"
    assert not seed_path.exists()


def test_write_seed_without_o_nofollow_attr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Bugbot regression: O_NOFOLLOW is POSIX-only. On a platform lacking it the
    # write must still succeed (getattr → 0), not raise AttributeError that would
    # bubble out of _annotate_mcp_results_for_citations and blank the Sources
    # block.
    monkeypatch.delattr(mcp_cmd.os, "O_NOFOLLOW", raising=False)
    seed_path = tmp_path / ".unique" / "mcp-refs-seed.json"

    mcp_cmd._write_mcp_refs_seed(seed_path, 4)

    assert json.loads(seed_path.read_text(encoding="utf-8")) == {"maxSourceNumber": 4}


# ── Sources block names the tool (UN-23199) ──────────────────────────────────


def test_sources_block_includes_tool_name(tmp_path: Path) -> None:
    response = _FakeMCPResponse(
        content=[{"type": "resource_link", "uri": "https://e/a", "name": "Doc A"}]
    )
    out = _run("mcp__kb__fetch", response)
    assert "[mcpsource1] Doc A — mcp__kb__fetch" in out


def test_sources_block_titleless_uses_tool_name(tmp_path: Path) -> None:
    response = _FakeMCPResponse(content=[{"type": "text", "text": "status: ok"}])
    out = _run("mcp__crm__update", response)
    assert "[mcpsource1] mcp__crm__update" in out


# ── Title-less dedup by content hash (UN-23199) ──────────────────────────────


def test_titleless_distinct_text_gets_distinct_numbers(tmp_path: Path) -> None:
    # Two title-less fetches through one tool returning different bodies must not
    # collapse onto one source number (content-hash in the dedup key).
    _run(
        "mcp__crm__update",
        _FakeMCPResponse(content=[{"type": "text", "text": "a"}]),
        formatted="alpha result",
    )
    _run(
        "mcp__crm__update",
        _FakeMCPResponse(content=[{"type": "text", "text": "b"}]),
        formatted="beta result",
    )
    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert len(refs) == 2
    assert {r["sourceNumber"] for r in refs} == {1, 2}


def test_titleless_identical_text_still_merges(tmp_path: Path) -> None:
    # Identical title-less bodies through one tool still merge onto one source.
    for _ in range(2):
        _run(
            "mcp__crm__update",
            _FakeMCPResponse(content=[{"type": "text", "text": "same"}]),
            formatted="identical",
        )
    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert len(refs) == 1
    assert refs[0]["sourceNumber"] == 1


def test_titleless_oversized_identical_text_merges_across_calls(
    tmp_path: Path,
) -> None:
    # Bugbot regression: the dedup key must hash the CAPPED text so the second
    # call (rebuilding the key from the truncated manifest entry) still matches
    # the first (full live text). An oversized identical title-less body must
    # merge onto one source, not be re-assigned a duplicate number.
    big = "x" * (mcp_cmd._MCP_REF_TEXT_CHAR_LIMIT + 50)
    for _ in range(2):
        _run(
            "mcp__crm__update",
            _FakeMCPResponse(content=[{"type": "text", "text": "plain"}]),
            formatted=big,
        )
    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert len(refs) == 1
    assert refs[0]["sourceNumber"] == 1


# ── reference_mapping override (per-tool list destructuring) ──────────────────


def test_reference_mapping_destructures_wrapped_list_with_template(
    tmp_path: Path,
) -> None:
    # Atlassian-style: a non-JSON preamble wrapping issues under "issues", each
    # issue's title composed from key + nested fields.summary via titleTemplate.
    unique_dir = tmp_path / ".unique"
    body = json.dumps(
        {
            "issues": [
                {"key": "UN-1", "fields": {"summary": "First"}},
                {"key": "UN-2", "fields": {"summary": "Second"}},
            ]
        }
    )
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": f"[IMPORTANT: notice]\n{body}"}],
        mcp_server_id="atlassian",
    )
    footer = record_mcp_citations(
        response,
        tool_name="searchJiraIssuesUsingJql",
        server_name="atlassian",
        unique_dir=unique_dir,
        formatted_text=body,
        reference_mapping={
            "listPath": "issues",
            "titleTemplate": "{key} — {fields.summary}",
        },
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert {r["title"]: r["sourceNumber"] for r in refs} == {
        "UN-1 — First": 1,
        "UN-2 — Second": 2,
    }
    assert "[mcpsource1] UN-1 — First" in footer


def test_reference_mapping_writes_all_items_no_cap(tmp_path: Path) -> None:
    # Every retrieved record must get its own reference — the extractor no
    # longer caps the number of items per call.
    unique_dir = tmp_path / ".unique"
    n = 25
    body = json.dumps(
        {
            "issues": [
                {"key": f"UN-{i}", "fields": {"summary": f"s{i}"}} for i in range(n)
            ]
        }
    )
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": body}], mcp_server_id="atlassian"
    )
    record_mcp_citations(
        response,
        tool_name="searchJiraIssuesUsingJql",
        server_name="atlassian",
        unique_dir=unique_dir,
        formatted_text=body,
        reference_mapping={"listPath": "issues", "titlePath": "key"},
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert len(refs) == n
    assert {r["sourceNumber"] for r in refs} == set(range(1, n + 1))


def test_reference_mapping_title_from_text_for_markdown_doc(tmp_path: Path) -> None:
    # A fetched Markdown doc (non-JSON) titles its single chip from the leading
    # heading line when titleFromText is set, instead of the tool-name fallback.
    unique_dir = tmp_path / ".unique"
    doc = "# Retrieval Performance and Scalability Evaluation\n\nhttps://docs.unique.ai/x\n\nBody..."
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": doc}], mcp_server_id="docs"
    )
    record_mcp_citations(
        response,
        tool_name="read_doc",
        server_name="docs",
        unique_dir=unique_dir,
        formatted_text=doc,
        reference_mapping={"titleFromText": True, "titleMaxChars": 80},
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert [r["title"] for r in refs] == [
        "Retrieval Performance and Scalability Evaluation"
    ]


def test_reference_mapping_list_of_plain_strings_titled_from_text(
    tmp_path: Path,
) -> None:
    # A JSON array of plain-text documents: each item's title is its leading
    # line (Markdown heading markers stripped, capped).
    unique_dir = tmp_path / ".unique"
    body = json.dumps({"docs": ["# Alpha Guide\nbody", "## Beta Notes\nmore"]})
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    record_mcp_citations(
        response,
        tool_name="list_docs",
        server_name="docs",
        unique_dir=unique_dir,
        formatted_text=body,
        reference_mapping={"listPath": "docs", "titleFromText": True},
    )
    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert [r["title"] for r in refs] == ["Alpha Guide", "Beta Notes"]


def test_reference_mapping_list_of_objects_titled_from_text_field(
    tmp_path: Path,
) -> None:
    # A JSON array of objects whose title comes from a text body field, with a
    # separate details field per item.
    unique_dir = tmp_path / ".unique"
    body = json.dumps(
        {
            "results": [
                {"content": "# Gamma\nx", "updated": "2026-01-01"},
                {"content": "Delta\ny", "updated": "2026-02-02"},
            ]
        }
    )
    response = _FakeMCPResponse(content=[{"type": "text", "text": body}])
    record_mcp_citations(
        response,
        tool_name="search_text_docs",
        server_name="docs",
        unique_dir=unique_dir,
        formatted_text=body,
        reference_mapping={
            "listPath": "results",
            "titleFromText": True,
            "titleTextPath": "content",
            "detailsPath": "updated",
        },
    )
    refs = _lines(tmp_path, _REFS_MANIFEST)
    assert {r["title"]: r["details"] for r in refs} == {
        "Gamma": "2026-01-01",
        "Delta": "2026-02-02",
    }


def test_reference_mapping_falls_back_to_heuristic_when_no_match(
    tmp_path: Path,
) -> None:
    # listPath points nowhere → mapping yields nothing → the generic JSON-title
    # heuristic still extracts the top-level title.
    unique_dir = tmp_path / ".unique"
    body = json.dumps({"title": "Lonely Page"})
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": body}], mcp_server_id="atlassian"
    )
    record_mcp_citations(
        response,
        tool_name="getConfluencePage",
        server_name="atlassian",
        unique_dir=unique_dir,
        formatted_text=body,
        reference_mapping={"listPath": "does_not_exist", "titlePath": "key"},
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert [r["title"] for r in refs] == ["Lonely Page"]


def test_reference_mapping_title_from_text_does_not_block_list_heuristic(
    tmp_path: Path,
) -> None:
    # A mapping that finds list records but resolves no per-record title must not
    # fall through to titleFromText (a bogus single text chip). It should defer
    # to the generic heuristic so each issue still becomes its own reference.
    unique_dir = tmp_path / ".unique"
    body = json.dumps(
        {
            "issues": [
                {"key": "UN-1", "fields": {"summary": "First"}},
                {"key": "UN-2", "fields": {"summary": "Second"}},
            ]
        }
    )
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": body}], mcp_server_id="atlassian"
    )
    record_mcp_citations(
        response,
        tool_name="searchJiraIssuesUsingJql",
        server_name="atlassian",
        unique_dir=unique_dir,
        formatted_text=body,
        reference_mapping={
            "listPath": "issues",
            "titlePath": "nonexistent",
            "titleFromText": True,
        },
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert {r["title"]: r["sourceNumber"] for r in refs} == {"UN-1": 1, "UN-2": 2}


def test_reference_mapping_empty_structured_content_still_titles_from_text(
    tmp_path: Path,
) -> None:
    # An empty structuredContent object must not count as a located record: it
    # carries no data, so titleFromText should still title the chip from the
    # leading Markdown heading instead of falling back to the tool-name chip.
    unique_dir = tmp_path / ".unique"
    doc = "# Quarterly Planning Notes\n\nBody..."
    response = _FakeMCPResponse(
        content=[{"type": "text", "text": doc}], mcp_server_id="docs"
    )
    response.structured_content = {}
    record_mcp_citations(
        response,
        tool_name="read_doc",
        server_name="docs",
        unique_dir=unique_dir,
        formatted_text=doc,
        reference_mapping={"titleFromText": True, "titleMaxChars": 80},
    )
    refs = _unique_lines(unique_dir, "mcp-refs.jsonl")
    assert [r["title"] for r in refs] == ["Quarterly Planning Notes"]
