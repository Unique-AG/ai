"""MCP command: call MCP server tools via the Unique platform."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import unique_sdk
from unique_sdk.cli.commands._citation_manifest import (
    UnsafeRefsLogPathError,
    _append_turn_refs_manifest_entry,
    _locked_turn_refs_manifest,
    _read_turn_refs_manifest,
    _rewrite_turn_refs_manifest,
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
# This manifest is the groundedness check's source of truth, so the cap is
# sized against the eval model's context window rather than kept minimal:
# GPT-4o's 128k-token input fits ~400k chars, and the runner bounds the
# combined per-turn payload separately (UN-22309). At the previous 50k, a
# large list result (e.g. a 115k-char Jira search) lost most of its items
# before the judge saw them, flagging well-grounded answers as hallucinations.
_MCP_OUTPUT_TEXT_CHAR_LIMIT = 200_000

# Per-turn manifest of citable MCP sources, consumed by the runner to stitch
# ``[mcpsourceN]`` markers into ``<sup>N</sup>`` footnotes + reference chips
# (UN-21285). One entry per retrieved item: a short *title* describing what was
# retrieved (no URL — those are technical/misleading). The runner labels the
# chip with that title + the MCP tool name; falls back to the tool alone when
# the result carries no recognizable title.
_MCP_REFS_LOG_RELATIVE_PATH = Path(".unique") / "mcp-refs.jsonl"
_MCP_REFS_LOCK_FILENAME = "mcp-refs.lock"
# Persistent per-chat seed for ``[mcpsourceN]`` numbering. The SI runner wipes
# ``mcp-refs.jsonl`` between turns, so manifest-derived numbering restarts at 1
# every turn; this sibling file records the highest source number ever assigned
# in the chat so numbering stays monotonic across turns (UN-23199). Body is
# ``{"maxSourceNumber": <int>}``; the monorepo runner preserves this file across
# its per-turn reset. Absent/unreadable → seed 0 → identical to pre-seed
# behavior (forward/backward compatible).
_MCP_REFS_SEED_FILENAME = "mcp-refs-seed.json"
_MCP_SNIPPET_CHAR_LIMIT = 300
# Writer-side cap on the per-item ``text`` recorded in the refs manifest — the
# cited item's underlying text, consumed by the runner's hallucination check to
# ground each ``[mcpsourceN]`` citation on what was actually retrieved
# (UN-22762). Half the flat-output cap (``_MCP_OUTPUT_TEXT_CHAR_LIMIT``): one
# cited item (a page, an issue record) rarely exceeds it, and the eval side
# bounds the combined cited-text payload separately.
_MCP_REF_TEXT_CHAR_LIMIT = 100_000

# Keys an MCP tool's JSON result commonly uses for a record's human title.
_TITLE_KEYS = ("title", "name", "displayName", "subject", "summary", "key")

# Keys an MCP tool's JSON result commonly uses for the optional "details" line
# (UN-22310) — e.g. a date and an author such as "10/10/2026 - Jamie Dimon".
# Best-effort: only top-level record keys are inspected for these (nested
# provenance is too tool-specific to generalize). The values themselves may be
# nested one level — a date is read as a top-level string, while an author may
# be a plain string or an object whose name is pulled via `_AUTHOR_NAME_KEYS`
# (e.g. Atlassian's `{"displayName": "..."}`). The line is omitted when neither
# a date nor an author is found.
_DETAILS_DATE_KEYS = (
    "date",
    "updated",
    "updatedAt",
    "updatedDate",
    "lastModified",
    "modified",
    "created",
    "createdAt",
    "createdDate",
    "timestamp",
)
_DETAILS_AUTHOR_KEYS = (
    "author",
    "creator",
    "owner",
    "createdBy",
    "updatedBy",
    "by",
    "sender",
    "from",
)
# Keys to read a human name out of an author value that is itself an object
# (e.g. Atlassian's ``{"displayName": "Jamie Dimon"}``).
_AUTHOR_NAME_KEYS = ("displayName", "name", "fullName", "emailAddress", "email")
_MCP_DETAILS_CHAR_LIMIT = 200

# Canonical ``toolName`` written to both manifests: the **bare advertised tool
# name** (the payload ``name`` the agent passes to ``unique-cli mcp``).
# ``unique-cli mcp`` only runs in skills mode, where the agent invokes a tool by
# its bare advertised name (the SI ``mcp_skill_generator`` renders the example
# payload with that bare name). The SI runner therefore resolves a friendly
# display label by keying its tool-config map on this bare name. The
# ``mcp__<server>__<tool>`` parsing below is a defensive fallback for that
# double-underscore convention and does not fire in skills mode; there
# ``serverName`` is sourced from ``response.mcpServerId`` instead (see
# ``cmd_mcp``).


def _server_name_from_tool(name: str) -> str | None:
    """Best-effort server name for the ``mcp__<server>__<tool>`` convention.

    Defensive only — the bare advertised tool name carries no ``mcp__`` prefix
    in skills mode (the only mode that runs this command), so this returns
    ``None`` there and the caller falls back to ``response.mcpServerId``.
    """
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


def _first_str_by_keys(obj: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _author_display(obj: dict[str, Any]) -> str | None:
    """Read an author name from a record, whether the author value is a plain
    string or a nested object (e.g. ``{"displayName": "..."}``)."""
    for key in _DETAILS_AUTHOR_KEYS:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            name = _first_str_by_keys(value, _AUTHOR_NAME_KEYS)
            if name:
                return name
    return None


def _details_from_json(obj: dict[str, Any]) -> str | None:
    """Best-effort optional "details" line (UN-22310): a date and/or author
    composed as "<date> - <author>". Returns ``None`` when neither is found."""
    date = _first_str_by_keys(obj, _DETAILS_DATE_KEYS)
    author = _author_display(obj)
    parts = [part for part in (date, author) if part]
    if not parts:
        return None
    return " - ".join(parts)[:_MCP_DETAILS_CHAR_LIMIT]


# Keys under which a JSON object commonly wraps the actual list of retrieved
# records, e.g. Jira's ``{"issues": [...]}`` or a generic ``{"results": [...]}``.
# When a result wraps its records this way, we iterate the list so each record
# becomes its own reference instead of collapsing to one title-less chip.
_CONTAINER_KEYS = (
    "issues",
    "results",
    "items",
    "values",
    "data",
    "hits",
    "records",
    "entries",
    "elements",
    "content",
)

# Subset of ``_CONTAINER_KEYS`` that are also plausible fields of a *single*
# titled record — e.g. a page/document payload ``{"title": ..., "content": [...]}``
# whose ``content`` is the body, not a list of separate results. When one of
# these matches on an object that carries its own top-level title, we keep the
# object as one record rather than splitting it into title-less inner rows.
_AMBIGUOUS_CONTAINER_KEYS = ("data", "content")


def _loads_embedded_json(text: str) -> Any:
    """Parse a JSON value from a tool-result string, tolerating a non-JSON
    preamble.

    Some MCP servers (e.g. Atlassian) prefix the JSON body with a human-readable
    notice like ``[IMPORTANT: ...]\\n{...}``, so a direct ``json.loads`` of the
    whole string fails. Try a direct parse first, then fall back to decoding the
    first JSON object/array that appears. Returns ``None`` when no JSON is found.
    """
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char in "{[":
            try:
                value, _ = decoder.raw_decode(text, index)
            except ValueError:
                continue
            return value
    return None


def _records_from_parsed(parsed: Any) -> list[dict[str, Any]]:
    """Normalize a parsed JSON value to a flat list of record dicts, unwrapping
    a single container key (``{"issues": [...]}``) when present."""
    if isinstance(parsed, list):
        return [entry for entry in parsed if isinstance(entry, dict)]
    if isinstance(parsed, dict):
        for key in _CONTAINER_KEYS:
            value = parsed.get(key)
            if isinstance(value, list):
                records = [entry for entry in value if isinstance(entry, dict)]
                if records:
                    # A single titled record must not be split apart by an
                    # incidental ambiguous key (a page body under ``content`` /
                    # ``data``) — keep the object as one record so its title
                    # survives instead of collapsing to a title-less chip.
                    if key in _AMBIGUOUS_CONTAINER_KEYS and _title_from_json(parsed):
                        return [parsed]
                    return records
        return [parsed]
    return []


def _titles_from_json(text: str) -> list[dict[str, Any]]:
    """Best-effort: pull a human title out of a JSON result, e.g. an Atlassian
    page/issue returned as JSON-in-text. Tolerates a non-JSON preamble before
    the JSON body and unwraps a container key (``{"issues": [...]}``) so each
    retrieved record yields its own item. Returns [] when the text carries no
    JSON or no record has a recognizable title.
    """
    parsed = _loads_embedded_json(text)
    if parsed is None:
        return []
    items: list[dict[str, Any]] = []
    for entry in _records_from_parsed(parsed):
        title = _title_from_json(entry)
        if title:
            items.append(
                {
                    "title": title,
                    "snippet": None,
                    "details": _details_from_json(entry),
                    "text": _record_text(entry),
                }
            )
    return items


def _get_by_dotted_path(obj: Any, path: str) -> Any:
    """Walk a dotted path over dicts and lists (numeric segments index lists),
    e.g. ``"issues"``, ``"fields.summary"``, ``"result.items.0.key"``. Returns
    ``None`` when any segment is missing."""
    current = obj
    for segment in path.split("."):
        if isinstance(current, dict):
            current = current.get(segment)
        elif isinstance(current, list) and segment.lstrip("-").isdigit():
            index = int(segment)
            try:
                current = current[index]
            except IndexError:
                return None
        else:
            return None
        if current is None:
            return None
    return current


_TEMPLATE_TOKEN = re.compile(r"\{([^{}]+)\}")


def _render_title_template(template: str, record: dict[str, Any]) -> str | None:
    """Substitute ``{dotted.path}`` tokens from ``record`` into ``template``.
    Missing tokens render empty; returns ``None`` if the result is blank."""

    def _sub(match: re.Match[str]) -> str:
        value = _get_by_dotted_path(record, match.group(1).strip())
        return str(value).strip() if value is not None else ""

    rendered = _TEMPLATE_TOKEN.sub(_sub, template).strip()
    # Collapse artifacts left by empty tokens (e.g. a dangling " — ").
    rendered = rendered.strip(" -—–|:").strip()
    return rendered or None


def _mapped_records(response: Any, list_path: str | None) -> list[Any]:
    """Locate the records a reference mapping applies to, preferring the
    MCP-native ``structuredContent`` then any JSON-in-text block (preamble
    tolerant). ``list_path`` (dotted) points at the array; when unset the parsed
    value itself is used. List entries may be objects (field/template titles) or
    plain strings (text titles), so both are kept; a single object is wrapped.
    An empty object/list is ignored (not treated as a record) so the caller can
    still fall back to ``titleFromText`` / the generic heuristic — e.g. an empty
    ``structuredContent`` alongside a Markdown doc."""
    sources: list[Any] = []
    structured = getattr(response, "structuredContent", None) or getattr(
        response, "structured_content", None
    )
    if structured is not None:
        sources.append(structured)
    for block in getattr(response, "content", None) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parsed = _loads_embedded_json(block.get("text") or "")
            if parsed is not None:
                sources.append(parsed)

    for parsed in sources:
        target = _get_by_dotted_path(parsed, list_path) if list_path else parsed
        if isinstance(target, list):
            records = [entry for entry in target if isinstance(entry, (dict, str))]
            if records:
                return records
        elif isinstance(target, dict) and target:
            return [target]
    return []


_MCP_TEXT_TITLE_DEFAULT_CHARS = 120


def _leading_title_line(text: str | None, max_chars: int) -> str | None:
    """First non-empty line of ``text`` with leading Markdown heading/list
    markers (``# * - >``) stripped, capped at ``max_chars``. Used to title a
    plain-text document (or a plain-text list item) by its heading. ``None``
    when ``text`` is not a non-empty string."""
    if not isinstance(text, str):
        return None
    for line in text.splitlines():
        stripped = line.strip().lstrip("#*->").strip()
        if stripped:
            return stripped[:max_chars]
    return None


def _first_text_title(response: Any, max_chars: int) -> str | None:
    """Title from the first non-empty line of the first text block — for a
    non-JSON result such as a fetched Markdown document (e.g. ``read_doc``)."""
    for block in getattr(response, "content", None) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            title = _leading_title_line(block.get("text"), max_chars)
            if title:
                return title
    return None


def _all_text_blocks(response: Any) -> str | None:
    """Concatenation of every text block — the underlying text of a single-item
    result (e.g. a fetched document) recorded as that item's ground truth."""
    texts: list[str] = []
    for block in getattr(response, "content", None) or []:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text)
    return "\n\n".join(texts) or None


def _record_text(record: Any) -> str | None:
    """A record's underlying text for citation grounding: the record itself
    when it is a plain string, else the serialized record — which carries the
    titled field plus all metadata the agent may cite."""
    if isinstance(record, str):
        return record or None
    try:
        return json.dumps(record, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return None


def _extract_with_reference_mapping(
    response: Any, mapping: dict[str, Any]
) -> list[dict[str, Any]]:
    """Destructure a result into ``{title, snippet, details}`` items using an
    admin-configured reference mapping. For a list result, one item per record;
    for a non-JSON text result with ``titleFromText`` set, a single item titled
    from the leading text. Returns [] when the mapping locates nothing, so the
    caller can fall back to the generic heuristic."""
    list_path = mapping.get("listPath") or mapping.get("list_path")
    title_path = mapping.get("titlePath") or mapping.get("title_path")
    title_template = mapping.get("titleTemplate") or mapping.get("title_template")
    details_path = mapping.get("detailsPath") or mapping.get("details_path")
    title_from_text = mapping.get("titleFromText") or mapping.get("title_from_text")
    # When titling from text and the list items are objects, this dotted path
    # points at the text field within each item (e.g. ``content``); leave unset
    # when each item is itself a plain string.
    title_text_path = mapping.get("titleTextPath") or mapping.get("title_text_path")
    try:
        title_max_chars = int(
            mapping.get("titleMaxChars")
            or mapping.get("title_max_chars")
            or _MCP_TEXT_TITLE_DEFAULT_CHARS
        )
    except (TypeError, ValueError):
        title_max_chars = _MCP_TEXT_TITLE_DEFAULT_CHARS

    records = _mapped_records(response, list_path)
    items: list[dict[str, Any]] = []
    for record in records:
        is_dict = isinstance(record, dict)
        if title_from_text:
            # Title from the item's text: the item itself when it's a plain
            # string, else its ``title_text_path`` field.
            if isinstance(record, str):
                text = record
            elif is_dict and title_text_path:
                text = _get_by_dotted_path(record, title_text_path)
            else:
                text = None
            title = _leading_title_line(text, title_max_chars)
        elif title_template and is_dict:
            title = _render_title_template(title_template, record)
        elif title_path and is_dict:
            value = _get_by_dotted_path(record, title_path)
            title = str(value).strip() if isinstance(value, (str, int, float)) else None
        else:
            title = None
        if not title:
            continue
        details = (
            _get_by_dotted_path(record, details_path)
            if details_path and is_dict
            else None
        )
        items.append(
            {
                "title": title,
                "snippet": None,
                "details": str(details).strip() if details else None,
                "text": _record_text(record),
            }
        )
    if items:
        return items
    # Non-list / non-JSON result (e.g. a fetched Markdown doc): title the single
    # chip from the leading text when the tool opts in via ``titleFromText``.
    # Only when *no* records were located — if list records were found but
    # yielded no usable title, defer to the generic heuristic (e.g. per-issue
    # references) instead of a bogus text-derived chip.
    if not records and title_from_text:
        title = _first_text_title(response, title_max_chars)
        if title:
            return [
                {
                    "title": title,
                    "snippet": None,
                    "details": None,
                    "text": _all_text_blocks(response),
                }
            ]
    return items


def _extract_mcp_citation_items(
    response: Any,
    *,
    tool_name: str,
    server_name: str | None,
    reference_mapping: dict[str, Any] | None = None,
    fallback_text: str | None = None,
) -> list[dict[str, Any]]:
    """Context for what the tool retrieved: ``{title, snippet, text}`` per item.

    An optional admin ``reference_mapping`` is applied first (deterministic
    destructuring of a list result); when it yields nothing we fall back to the
    generic heuristic: MCP ``resource_link`` names (spec-native) or a best-effort
    JSON-title heuristic over text blocks (for tools like Atlassian that return
    JSON-in-text). No URLs are extracted — the chip is display-only. Falls back
    to a single title-less item (the runner names it after the tool) when the
    result carries no recognizable title.

    ``text`` is the item's underlying retrieved text (the serialized record, a
    fetched document body, or — for the title-less fallback — ``fallback_text``,
    the whole formatted output). The runner grounds the hallucination check for
    each cited ``[mcpsourceN]`` on it. A ``resource_link`` carries no body, so
    its ``text`` is the link description only.
    """
    if reference_mapping:
        mapped = _extract_with_reference_mapping(response, reference_mapping)
        if mapped:
            return mapped

    content = getattr(response, "content", None) or []
    items: list[dict[str, Any]] = []

    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "resource_link":
            name = (block.get("name") or "").strip()
            if name:
                items.append(
                    {
                        "title": name,
                        "snippet": _snippet(block.get("description")),
                        "text": block.get("description") or None,
                    }
                )

    if not items:
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                items.extend(_titles_from_json(block.get("text") or ""))

    if not items:
        # No recognizable title — one chip named after the tool itself.
        items.append({"title": None, "snippet": None, "text": fallback_text})

    return items


def _next_mcp_source_number(entries: list[dict[str, Any]]) -> int:
    numbers = [
        entry["sourceNumber"]
        for entry in entries
        if isinstance(entry.get("sourceNumber"), int)
    ]
    return max(numbers, default=0) + 1


def _read_mcp_refs_seed(seed_path: Path) -> int:
    """Read the persisted chat-wide ``maxSourceNumber`` from the seed file.

    Best-effort: returns ``0`` when the file is absent, unreadable, or malformed
    (never raises), so a missing seed reproduces the pre-seed numbering exactly.
    """
    try:
        raw = seed_path.read_text(encoding="utf-8")
        value = json.loads(raw).get("maxSourceNumber")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    except (OSError, ValueError, TypeError, AttributeError):
        return 0
    return 0


def _write_mcp_refs_seed(seed_path: Path, value: int) -> None:
    """Persist the chat-wide ``maxSourceNumber`` seed (best-effort, never raises).

    Only writes when ``value`` exceeds the currently persisted seed, so numbers
    never regress across turns.

    The temp file is opened with ``O_NOFOLLOW`` so a symlink pre-planted at the
    predictable temp path cannot redirect the write outside the refs directory
    (defense in depth on top of the per-user workspace sandbox). ``os.replace``
    operates on the directory entry and does not follow a symlink at the target.
    ``O_NOFOLLOW`` is POSIX-only; on platforms lacking it (e.g. Windows) it
    degrades to ``0`` via ``getattr`` rather than raising ``AttributeError`` —
    which, being outside the ``OSError`` handler, would otherwise bubble out of
    ``_annotate_mcp_results_for_citations`` after entries were written and blank
    the Sources block.
    """
    try:
        if value <= _read_mcp_refs_seed(seed_path):
            return
        seed_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = seed_path.with_suffix(seed_path.suffix + ".tmp")
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(tmp_path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"maxSourceNumber": value}))
        os.replace(tmp_path, seed_path)
    except OSError as exc:
        _LOGGER.warning("mcp: failed to write refs seed: %s", exc)


def _item_dedup_key(tool_name: str, item: dict[str, Any]) -> str:
    """Dedup by title when present (same item = one chip), else by tool + a short
    content hash of the item's text.

    Two distinct title-less fetches through one tool return different bodies, so
    hashing the text keeps them as separate sources instead of collapsing onto
    one number (identical bodies still merge). NOTE: this intentionally weakens
    the search-then-fetch text-upgrade merge for title-less items only — titled
    items still merge by title as before.

    The text is capped at ``_MCP_REF_TEXT_CHAR_LIMIT`` BEFORE hashing — the same
    cap the manifest stores under ``text``. Without it, the first call (live,
    full-length item text) and a later call rebuilding this key from the
    truncated manifest entry would hash to different values, so an oversized
    title-less result would be re-assigned a duplicate ``[mcpsourceN]`` instead
    of deduping.
    """
    title = item.get("title")
    if isinstance(title, str) and title.strip():
        return f"title:{tool_name}:{title.strip()}"
    capped_text = (item.get("text") or "")[:_MCP_REF_TEXT_CHAR_LIMIT]
    text_hash = hashlib.sha256(capped_text.encode("utf-8")).hexdigest()[:12]
    return f"tool:{tool_name}:{text_hash}"


def _ref_text(item: dict[str, Any]) -> str | None:
    """The item's underlying text for the manifest, capped at
    ``_MCP_REF_TEXT_CHAR_LIMIT`` (single write-side cap shared by all
    extraction modes)."""
    text = item.get("text")
    if not isinstance(text, str) or not text:
        return None
    return text[:_MCP_REF_TEXT_CHAR_LIMIT]


def _annotate_mcp_results_for_citations(
    response: Any,
    *,
    tool_name: str,
    server_name: str | None,
    refs_log_path: Path | None = None,
    reference_mapping: dict[str, Any] | None = None,
    fallback_text: str | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    """Assign per-turn ``[mcpsourceN]`` numbers to each retrieved item and append
    the refs manifest. Returns ``[(sourceNumber, item)]`` for the Sources block.

    Items dedup by title across the turn (same item keeps one number); a
    title-less item dedups by tool plus a content hash of its (capped) text, so
    two distinct title-less results through one tool get distinct numbers while
    identical bodies still merge (this weakens the search-then-fetch text-upgrade
    merge for title-less items only). Best-effort — returns ``[]`` on any failure
    (the tool result is unaffected; only the citation Sources block is skipped).
    """
    refs_log_path = refs_log_path or (Path.cwd() / _MCP_REFS_LOG_RELATIVE_PATH)
    annotated: list[tuple[int, dict[str, Any]]] = []
    try:
        items = _extract_mcp_citation_items(
            response,
            tool_name=tool_name,
            server_name=server_name,
            reference_mapping=reference_mapping,
            fallback_text=fallback_text,
        )
        with _locked_turn_refs_manifest(
            refs_log_path, lock_filename=_MCP_REFS_LOCK_FILENAME
        ):
            entries = _read_turn_refs_manifest(refs_log_path)
            # Chat-wide monotonic seed: the runner wipes ``mcp-refs.jsonl``
            # between turns, so manifest-derived numbering restarts at 1 each
            # turn. The seed file (preserved across the runner's per-turn reset)
            # records the highest number ever assigned in the chat so a fresh
            # number exceeds both the current manifest max AND the chat-wide max.
            seed_path = refs_log_path.parent / _MCP_REFS_SEED_FILENAME
            seed = _read_mcp_refs_seed(seed_path)
            highest_assigned = seed
            numbers_by_key: dict[str, int] = {}
            for entry in entries:
                if isinstance(entry.get("sourceNumber"), int):
                    stored_tool = entry.get("toolName") or tool_name
                    numbers_by_key[_item_dedup_key(stored_tool, entry)] = entry[
                        "sourceNumber"
                    ]
            entries_by_number = {
                entry["sourceNumber"]: entry
                for entry in entries
                if isinstance(entry.get("sourceNumber"), int)
            }
            needs_rewrite = False
            for item in items:
                key = _item_dedup_key(tool_name, item)
                source_number = numbers_by_key.get(key)
                if source_number is None:
                    source_number = max(_next_mcp_source_number(entries), seed + 1)
                    manifest_entry = {
                        "sourceNumber": source_number,
                        "toolName": tool_name,
                        "serverName": server_name,
                        "title": item.get("title"),
                        "snippet": item.get("snippet"),
                        "details": item.get("details"),
                        "text": _ref_text(item),
                    }
                    try:
                        _append_turn_refs_manifest_entry(refs_log_path, manifest_entry)
                    except (UnsafeRefsLogPathError, OSError) as exc:
                        _LOGGER.warning(
                            "mcp: failed to append refs manifest entry: %s", exc
                        )
                        break
                    numbers_by_key[key] = source_number
                    entries.append(manifest_entry)
                    entries_by_number[source_number] = manifest_entry
                    highest_assigned = max(highest_assigned, source_number)
                else:
                    # Deduped: a prior call already claimed this source number.
                    # Backfill ``details`` the first call may have lacked (the
                    # runner reads one entry per source number, so enriching it
                    # in place is sufficient) — only when newly extracted.
                    stored = entries_by_number.get(source_number)
                    new_details = item.get("details")
                    if stored is not None and new_details and not stored.get("details"):
                        stored["details"] = new_details
                        needs_rewrite = True
                    # ``text`` upgrades to the longer capture: the common turn
                    # is a search (small per-record JSON) followed by a full
                    # fetch of the same titled item — the later, richer text is
                    # the better ground truth for the hallucination check.
                    new_text = _ref_text(item)
                    if stored is not None and new_text:
                        stored_text = stored.get("text")
                        stored_len = (
                            len(stored_text) if isinstance(stored_text, str) else 0
                        )
                        if len(new_text) > stored_len:
                            stored["text"] = new_text
                            needs_rewrite = True
                annotated.append((source_number, item))
            if needs_rewrite:
                try:
                    _rewrite_turn_refs_manifest(refs_log_path, entries)
                except (UnsafeRefsLogPathError, OSError) as exc:
                    _LOGGER.warning(
                        "mcp: failed to backfill refs manifest enrichment: %s", exc
                    )
            # Persist the chat-wide max so next turn's numbering continues above
            # it even after the runner wipes ``mcp-refs.jsonl``.
            if highest_assigned > seed:
                _write_mcp_refs_seed(seed_path, highest_assigned)
    except (UnsafeRefsLogPathError, OSError) as exc:
        _LOGGER.warning("mcp: failed to append refs manifest: %s", exc)
        return []
    except Exception as exc:  # noqa: BLE001 — never break the tool call
        _LOGGER.warning("mcp: failed to extract citations: %s", exc)
        return []
    return annotated


def _citation_sources_block(
    annotated: list[tuple[int, dict[str, Any]]], *, tool_name: str
) -> str:
    """Tell the agent which marker to cite each retrieved item with.

    Rendered *before* the tool output (leading block, not a trailing footer):
    the agent harness spills oversized tool results to a file wholesale, and a
    partial or programmatic read of that file only reliably sees the head — a
    trailing marker list would be exactly what such reads miss (UN-22309).

    Each line names the ``tool_name`` alongside the marker so the model has a
    stronger anchor than a bare integer: ``{title} — {tool_name}`` when the item
    carries a title, or ``{tool_name}`` for the title-less fallback.
    """
    if not annotated:
        return ""
    lines = [
        "Sources — MANDATORY: every fact you take from this result MUST be "
        "cited inline with its [mcpsourceN] marker from this list, or it "
        "will not be referenced in the answer:",
    ]
    for source_number, item in annotated:
        title = item.get("title")
        if isinstance(title, str) and title.strip():
            label = f"{title.strip()} — {tool_name}"
        else:
            label = tool_name
        lines.append(f"  [mcpsource{source_number}] {label}")
    return "\n".join(lines)


def _append_mcp_output_manifest(
    name: str,
    text: str,
    *,
    server_name: str | None = None,
    output_path: Path | None = None,
) -> None:
    """Best-effort append of one MCP tool result to the per-turn manifest.

    Never raises: a manifest failure must not change what the agent sees as
    the tool result. The groundedness check simply does not fire for this
    call when the write fails.

    ``output_path`` is the full path of the ``mcp-output.jsonl`` manifest. It
    defaults to ``Path.cwd() / .unique / mcp-output.jsonl`` so the CLI flow
    (where cwd is the agent workspace) is unchanged; callers that run outside
    the workspace cwd (e.g. the in-process tools-mode proxy) pass it explicitly.
    """
    try:
        refs_log_path = output_path or (Path.cwd() / _MCP_OUTPUT_LOG_RELATIVE_PATH)
        _append_turn_refs_manifest_entry(
            refs_log_path,
            {
                "toolName": name,
                "serverName": server_name,
                "text": text[:_MCP_OUTPUT_TEXT_CHAR_LIMIT],
            },
        )
    except (UnsafeRefsLogPathError, OSError) as exc:
        _LOGGER.warning("mcp: failed to append output manifest: %s", exc)


def record_mcp_citations(
    response: Any,
    *,
    tool_name: str,
    server_name: str | None,
    unique_dir: Path,
    formatted_text: str,
    reference_mapping: dict[str, Any] | None = None,
) -> str:
    """Write both per-turn MCP manifests under ``unique_dir`` and return the
    ``[mcpsourceN]`` citation Sources block for the agent.

    Callers must place the block *before* the tool output (leading block, not
    a trailing footer) so the markers survive harness-side spilling/truncation
    of large results (UN-22309). Shared by the ``unique-cli mcp`` skills flow
    (``cmd_mcp``) and the in-process tools-mode proxy in assistants-core, so
    both write identical manifests and blocks. ``unique_dir`` is the workspace
    ``.unique`` directory (its filenames are joined directly here — do not
    pass the workspace root).

    - ``response`` is the raw ``unique_sdk.MCP`` result, used for citation
      extraction (titles from ``resource_link`` names / JSON bodies).
    - ``formatted_text`` is the source text the model actually saw for this
      tool result, recorded as the hallucination groundedness context. It also
      serves as the per-item ``text`` of the title-less fallback chip, so a
      cited ``[mcpsourceN]`` without extractable records still grounds on the
      whole output.

    Best-effort and never raises: the underlying manifest writers swallow their
    own errors, and ``_annotate_mcp_results_for_citations`` owns the per-turn
    file lock — this function must stay lock-free to avoid a same-process flock
    self-deadlock.
    """
    _append_mcp_output_manifest(
        tool_name,
        formatted_text,
        server_name=server_name,
        output_path=unique_dir / _MCP_OUTPUT_LOG_RELATIVE_PATH.name,
    )
    annotated = _annotate_mcp_results_for_citations(
        response,
        tool_name=tool_name,
        server_name=server_name,
        refs_log_path=unique_dir / _MCP_REFS_LOG_RELATIVE_PATH.name,
        reference_mapping=reference_mapping,
        fallback_text=formatted_text,
    )
    return _citation_sources_block(annotated, tool_name=tool_name)


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

    server_name = _server_name_from_tool(name) or getattr(response, "mcpServerId", None)
    sources_block = record_mcp_citations(
        response,
        tool_name=name,
        server_name=server_name,
        unique_dir=Path.cwd() / ".unique",
        formatted_text=formatted,
        reference_mapping=state.mcp_tool_reference_mappings.get(name),
    )
    # Sources block FIRST: large outputs get spilled/truncated tail-first by
    # the agent harness, and a trailing block is what partial reads miss.
    if sources_block:
        return sources_block + "\n\n" + formatted
    return formatted
