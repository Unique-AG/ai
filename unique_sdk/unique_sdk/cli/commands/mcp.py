"""MCP command: call MCP server tools via the Unique platform."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import unique_sdk
from unique_sdk.cli.commands._citation_manifest import (
    UnsafeRefsLogPathError,
    _append_turn_refs_manifest_entry,
    _locked_turn_refs_manifest,
    _read_turn_refs_manifest,
)
from unique_sdk.cli.formatting import format_mcp_response
from unique_sdk.cli.state import ShellState

_LOGGER = logging.getLogger(__name__)

# Per-turn manifest of MCP tool output text, consumed by the Swappable
# Intelligence runner to ground the hallucination check against MCP-retrieved
# information (UN-21951). Carries *text only* — no source numbers/markers
# (referencing is UN-21285, tracked separately).
_MCP_OUTPUT_LOG_RELATIVE_PATH = Path(".unique") / "mcp-output.jsonl"
# Writer-side cap so a single huge/raw tool result cannot bloat the manifest.
# The evaluator applies its own per-source cap as well.
_MCP_OUTPUT_TEXT_CHAR_LIMIT = 50_000

# Per-turn manifest of citable MCP sources, consumed by the runner to stitch
# ``[mcpsourceN]`` markers into ``<sup>N</sup>`` footnotes + reference chips
# (UN-21285). One entry per retrieved item: a short *title* describing what was
# retrieved (no URL — those are technical/misleading). The runner labels the
# chip with that title + the MCP tool name; falls back to the tool alone when
# the result carries no recognizable title.
_MCP_REFS_LOG_RELATIVE_PATH = Path(".unique") / "mcp-refs.jsonl"
_MCP_REFS_LOCK_FILENAME = "mcp-refs.lock"
_MCP_SNIPPET_CHAR_LIMIT = 300
_MCP_MAX_ITEMS_PER_CALL = 8

# Keys an MCP tool's JSON result commonly uses for a record's human title.
_TITLE_KEYS = ("title", "name", "displayName", "subject", "summary", "key")


def _server_name_from_tool(name: str) -> str | None:
    """Best-effort server name for the ``mcp__<server>__<tool>`` convention."""
    parts = name.split("__")
    if len(parts) >= 3 and parts[0] == "mcp":
        return parts[1]
    return None


def _snippet(text: str | None) -> str | None:
    if not isinstance(text, str):
        return None
    collapsed = " ".join(text.split())
    return collapsed[:_MCP_SNIPPET_CHAR_LIMIT] or None


def _title_from_json(obj: dict[str, Any]) -> str | None:
    for key in _TITLE_KEYS:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _titles_from_json(text: str) -> list[dict[str, Any]]:
    """Best-effort: pull a human title out of a JSON result (object or list of
    objects), e.g. an Atlassian page/issue returned as JSON-in-text. Returns []
    when the text is not JSON or carries no recognizable title.
    """
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return []
    candidates = parsed if isinstance(parsed, list) else [parsed]
    items: list[dict[str, Any]] = []
    for entry in candidates:
        if isinstance(entry, dict):
            title = _title_from_json(entry)
            if title:
                items.append({"title": title, "snippet": None})
    return items


def _extract_mcp_citation_items(
    response: Any,
    *,
    tool_name: str,
    server_name: str | None,
) -> list[dict[str, Any]]:
    """Context for what the tool retrieved: ``{title, snippet}`` per item.

    Titles come from MCP ``resource_link`` names (spec-native) or a best-effort
    JSON-title heuristic over text blocks (for tools like Atlassian that return
    JSON-in-text). No URLs are extracted — the chip is display-only. Falls back
    to a single title-less item (the runner names it after the tool) when the
    result carries no recognizable title.
    """
    content = getattr(response, "content", None) or []
    items: list[dict[str, Any]] = []

    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "resource_link":
            name = (block.get("name") or "").strip()
            if name:
                items.append(
                    {"title": name, "snippet": _snippet(block.get("description"))}
                )

    if not items:
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                items.extend(_titles_from_json(block.get("text") or ""))

    if not items:
        # No recognizable title — one chip named after the tool itself.
        items.append({"title": None, "snippet": None})

    return items[:_MCP_MAX_ITEMS_PER_CALL]


def _next_mcp_source_number(entries: list[dict[str, Any]]) -> int:
    numbers = [
        entry["sourceNumber"]
        for entry in entries
        if isinstance(entry.get("sourceNumber"), int)
    ]
    return max(numbers, default=0) + 1


def _item_dedup_key(tool_name: str, item: dict[str, Any]) -> str:
    """Dedup by title when present (same item = one chip), else by tool."""
    title = item.get("title")
    if isinstance(title, str) and title.strip():
        return f"title:{tool_name}:{title.strip()}"
    return f"tool:{tool_name}"


def _annotate_mcp_results_for_citations(
    response: Any,
    *,
    tool_name: str,
    server_name: str | None,
    refs_log_path: Path | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    """Assign per-turn ``[mcpsourceN]`` numbers to each retrieved item and append
    the refs manifest. Returns ``[(sourceNumber, item)]`` for the footer.

    Items dedup by title across the turn (same item keeps one number), or by
    tool for the title-less fallback. Best-effort — returns ``[]`` on any failure
    (the tool result is unaffected; only the citation footer is skipped).
    """
    refs_log_path = refs_log_path or (Path.cwd() / _MCP_REFS_LOG_RELATIVE_PATH)
    annotated: list[tuple[int, dict[str, Any]]] = []
    try:
        items = _extract_mcp_citation_items(
            response, tool_name=tool_name, server_name=server_name
        )
        with _locked_turn_refs_manifest(
            refs_log_path, lock_filename=_MCP_REFS_LOCK_FILENAME
        ):
            entries = _read_turn_refs_manifest(refs_log_path)
            numbers_by_key: dict[str, int] = {}
            for entry in entries:
                if isinstance(entry.get("sourceNumber"), int):
                    stored_tool = entry.get("toolName") or tool_name
                    numbers_by_key[_item_dedup_key(stored_tool, entry)] = entry[
                        "sourceNumber"
                    ]
            for item in items:
                key = _item_dedup_key(tool_name, item)
                source_number = numbers_by_key.get(key)
                if source_number is None:
                    source_number = _next_mcp_source_number(entries)
                    manifest_entry = {
                        "sourceNumber": source_number,
                        "toolName": tool_name,
                        "serverName": server_name,
                        "title": item.get("title"),
                        "snippet": item.get("snippet"),
                    }
                    numbers_by_key[key] = source_number
                    entries.append(manifest_entry)
                    _append_turn_refs_manifest_entry(refs_log_path, manifest_entry)
                annotated.append((source_number, item))
    except (UnsafeRefsLogPathError, OSError) as exc:
        _LOGGER.warning("mcp: failed to append refs manifest: %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001 — never break the tool call
        _LOGGER.warning("mcp: failed to extract citations: %s", exc)
        return []
    return annotated


def _citation_footer(annotated: list[tuple[int, dict[str, Any]]]) -> str:
    """Tell the agent which marker to cite each retrieved item with."""
    if not annotated:
        return ""
    lines = ["", "Sources — cite each fact with the marker for the item it came from:"]
    for source_number, item in annotated:
        label = item.get("title") or "this MCP tool result"
        lines.append(f"  [mcpsource{source_number}] {label}")
    return "\n".join(lines)


def _append_mcp_output_manifest(name: str, text: str) -> None:
    """Best-effort append of one MCP tool result to the per-turn manifest.

    Never raises: a manifest failure must not change what the agent sees as
    the tool result. The groundedness check simply does not fire for this
    call when the write fails.
    """
    try:
        refs_log_path = Path.cwd() / _MCP_OUTPUT_LOG_RELATIVE_PATH
        _append_turn_refs_manifest_entry(
            refs_log_path,
            {
                "toolName": name,
                "serverName": _server_name_from_tool(name),
                "text": text[:_MCP_OUTPUT_TEXT_CHAR_LIMIT],
            },
        )
    except (UnsafeRefsLogPathError, OSError) as exc:
        _LOGGER.warning("mcp: failed to append output manifest: %s", exc)


def _read_payload(
    payload: str | None,
    file: str | None,
    stdin: bool,
) -> str:
    """Resolve the JSON payload from one of the three input sources."""
    sources = sum([payload is not None, file is not None, stdin])
    if sources == 0:
        raise ValueError(
            "No payload provided. Pass a JSON string, use --file, or --stdin."
        )
    if sources > 1:
        raise ValueError(
            "Ambiguous input: provide exactly one of PAYLOAD, --file, or --stdin."
        )

    if stdin:
        return sys.stdin.read()
    if file is not None:
        return Path(file).read_text(encoding="utf-8")
    assert payload is not None
    return payload


def _parse_and_validate(raw: str) -> tuple[str, dict[str, Any]]:
    """Parse JSON and validate the required ``name`` and ``arguments`` fields."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Payload must be a JSON object.")

    if "name" not in data:
        raise ValueError('Missing required field "name" in JSON payload.')

    name: str = data["name"]
    arguments: dict[str, Any] = data.get("arguments", {})

    if not isinstance(arguments, dict):
        raise ValueError('"arguments" must be a JSON object.')

    return name, arguments


def cmd_mcp(
    state: ShellState,
    chat_id: str,
    message_id: str,
    payload: str | None = None,
    file: str | None = None,
    stdin: bool = False,
) -> str:
    """Call an MCP tool with a JSON payload containing name and arguments."""
    try:
        raw = _read_payload(payload, file, stdin)
        name, arguments = _parse_and_validate(raw)

        response = unique_sdk.MCP.call_tool(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            name=name,
            chatId=chat_id,
            messageId=message_id,
            arguments=arguments,
        )

    except (ValueError, OSError, unique_sdk.APIError) as e:
        return f"mcp: {e}"

    try:
        formatted = format_mcp_response(response, tool_name=name)
    except Exception as fmt_exc:
        try:
            fallback = json.dumps(dict(response), indent=2, default=str)
        except Exception:
            fallback = repr(response)
        formatted = f"mcp: formatter error ({fmt_exc}); raw response:\n{fallback}"

    _append_mcp_output_manifest(name, formatted)

    server_name = _server_name_from_tool(name) or getattr(response, "mcpServerId", None)
    annotated = _annotate_mcp_results_for_citations(
        response, tool_name=name, server_name=server_name
    )
    return formatted + _citation_footer(annotated)
