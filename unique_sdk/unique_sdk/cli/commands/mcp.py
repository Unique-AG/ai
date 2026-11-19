"""MCP command: call MCP server tools via the Unique platform."""

from __future__ import annotations

import hashlib
import json
import logging
import os
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
from unique_sdk.cli.workspace import manifest_path as workspace_manifest_path
from unique_sdk.cli.workspace import unique_dir as workspace_unique_dir
from unique_sdk.utils.mcp_citations import extract_mcp_citation_items

_LOGGER = logging.getLogger(__name__)

MCP_ERROR_PREFIX = "mcp:"
_FORMATTER_ERROR_PREFIX = "mcp: formatter error"

# Per-turn manifest of MCP tool output text, consumed by the Swappable
# Intelligence runner to ground the hallucination check against MCP-retrieved
# information (UN-21951). Carries *text only* — no source numbers/markers
# (referencing is UN-21285, tracked separately).
_MCP_OUTPUT_LOG_RELATIVE_PATH = Path(".unique") / "mcp-output.jsonl"
# Runaway guard, four times the largest judge window; the runner trims by tokens.
_MCP_TEXT_GUARD_CHARS = 16_000_000
# Bytes of tool text each per-turn manifest may hold, about 16 judge windows.
_MCP_TURN_TEXT_BUDGET_BYTES = 64_000_000

# Per-turn manifest of citable MCP sources, consumed by the runner to stitch
# ``[mcpsourceN]`` markers into ``<sup>N</sup>`` footnotes + reference chips
# (UN-21285). One entry per retrieved item: a short *title* describing what was
# retrieved, plus that item's own http(s) link when the tool result includes
# one. The link is stored on the row and is not copied into the Sources block.
# The runner labels the chip with that title + the MCP tool name; falls back
# to the tool alone when the result carries no recognizable title.
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
    """
    title = item.get("title")
    if isinstance(title, str) and title.strip():
        return f"title:{tool_name}:{title.strip()}"
    text = (item.get("text") or "")[:_MCP_TEXT_GUARD_CHARS]
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"tool:{tool_name}:{text_hash}"


def _item_link_key(tool_name: str, item: dict[str, Any]) -> str | None:
    """Title-and-link key of a linked titled item, or None."""
    title = item.get("title")
    url = item.get("url")
    if isinstance(title, str) and title.strip() and isinstance(url, str) and url:
        return f"link:{tool_name}:{title.strip()}:{url}"
    return None


def _dedup_source_number(
    *,
    key: str,
    link_key: str | None,
    numbers_by_key: dict[str, int],
    entries_by_number: dict[int, dict[str, Any]],
) -> int | None:
    """Source number an item merges onto: same title and link, or same title when
    either side has no link."""
    if link_key is not None and link_key in numbers_by_key:
        return numbers_by_key[link_key]
    number = numbers_by_key.get(key)
    if number is None or link_key is None:
        return number
    stored_url = entries_by_number.get(number, {}).get("url")
    return None if stored_url else number


def _ref_text(item: dict[str, Any]) -> str | None:
    """The item's underlying text for the manifest, up to the runaway guard."""
    text = item.get("text")
    if not isinstance(text, str) or not text:
        return None
    return text[:_MCP_TEXT_GUARD_CHARS]


def _utf8_size(text: str) -> int:
    return len(text.encode("utf-8", errors="surrogatepass"))


def _within_bytes(text: str, room: int) -> str:
    """Longest prefix of ``text`` that fits ``room`` UTF-8 bytes."""
    if room <= 0:
        return ""
    encoded = text.encode("utf-8", errors="surrogatepass")
    if len(encoded) <= room:
        return text
    return encoded[:room].decode("utf-8", errors="ignore")


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

    Titled items dedup across the turn by title and link (same item keeps one
    number), or by title alone when either side has no link. A title-less item
    dedups by tool plus a content hash of its (capped) text, so two distinct
    title-less results through one tool get distinct numbers while identical
    bodies still merge (this weakens the search-then-fetch text-upgrade merge for
    title-less items only). Best-effort — returns ``[]`` on any failure
    (the tool result is unaffected; only the citation Sources block is skipped).
    """
    refs_log_path = refs_log_path or workspace_manifest_path(
        _MCP_REFS_LOG_RELATIVE_PATH
    )
    annotated: list[tuple[int, dict[str, Any]]] = []
    try:
        items = extract_mcp_citation_items(
            response,
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
                    stored_key = entry.get("dedupKey")
                    stored_tool = entry.get("toolName") or tool_name
                    if not isinstance(stored_key, str):
                        stored_key = _item_dedup_key(stored_tool, entry)
                    numbers_by_key.setdefault(stored_key, entry["sourceNumber"])
                    stored_link_key = _item_link_key(stored_tool, entry)
                    if stored_link_key is not None:
                        numbers_by_key[stored_link_key] = entry["sourceNumber"]
            entries_by_number = {
                entry["sourceNumber"]: entry
                for entry in entries
                if isinstance(entry.get("sourceNumber"), int)
            }
            needs_rewrite = False
            text_room = _MCP_TURN_TEXT_BUDGET_BYTES - sum(
                _utf8_size(entry["text"])
                for entry in entries
                if isinstance(entry.get("text"), str)
            )
            for item in items:
                key = _item_dedup_key(tool_name, item)
                link_key = _item_link_key(tool_name, item)
                source_number = _dedup_source_number(
                    key=key,
                    link_key=link_key,
                    numbers_by_key=numbers_by_key,
                    entries_by_number=entries_by_number,
                )
                if source_number is None:
                    source_number = max(_next_mcp_source_number(entries), seed + 1)
                    full_text = _ref_text(item) or ""
                    entry_text = _within_bytes(full_text, text_room)
                    text_room -= _utf8_size(entry_text)
                    manifest_entry = {
                        "sourceNumber": source_number,
                        "toolName": tool_name,
                        "serverName": server_name,
                        "title": item.get("title"),
                        "snippet": item.get("snippet"),
                        "details": item.get("details"),
                        "text": entry_text or None,
                    }
                    # Budget-cut text no longer hashes to the key, so it is kept.
                    if entry_text != full_text:
                        manifest_entry["dedupKey"] = key
                    item_url = item.get("url")
                    if isinstance(item_url, str) and item_url:
                        manifest_entry["url"] = item_url
                    try:
                        _append_turn_refs_manifest_entry(refs_log_path, manifest_entry)
                    except (UnsafeRefsLogPathError, OSError) as exc:
                        _LOGGER.warning(
                            "mcp: failed to append refs manifest entry: %s", exc
                        )
                        break
                    numbers_by_key.setdefault(key, source_number)
                    if link_key is not None:
                        numbers_by_key[link_key] = source_number
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
                    new_url = item.get("url")
                    if stored is not None and new_url and not stored.get("url"):
                        stored["url"] = new_url
                        needs_rewrite = True
                        if link_key is not None:
                            numbers_by_key[link_key] = source_number
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
                        growth = _utf8_size(new_text) - (
                            _utf8_size(stored_text)
                            if isinstance(stored_text, str)
                            else 0
                        )
                        if len(new_text) > stored_len and growth <= text_room:
                            text_room -= growth
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
    trailing marker list would be exactly what such reads miss.

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
    defaults to ``<workspace root>/.unique/mcp-output.jsonl``; callers outside
    the workspace (e.g. the in-process tools-mode proxy) pass it explicitly.
    """
    try:
        refs_log_path = output_path or workspace_manifest_path(
            _MCP_OUTPUT_LOG_RELATIVE_PATH
        )
        recorded = refs_log_path.stat().st_size if refs_log_path.is_file() else 0
        text = _within_bytes(
            text[:_MCP_TEXT_GUARD_CHARS], _MCP_TURN_TEXT_BUDGET_BYTES - recorded
        )
        if not text:
            _LOGGER.warning("mcp: turn output budget spent, row skipped")
            return
        _append_turn_refs_manifest_entry(
            refs_log_path,
            {
                "toolName": name,
                "serverName": server_name,
                "text": text,
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


class McpCommandResult(str):
    """Text returned by ``cmd_mcp``, with whether that call failed.

    Subclasses ``str`` so callers can print and search the text. ``failed``
    is set when the process should exit 1: a payload error, any
    ``UniqueError``, or a tool result with ``isError`` set.
    """

    failed: bool

    def __new__(cls, text: str, *, failed: bool) -> McpCommandResult:
        result = str.__new__(cls, text)
        result.failed = failed
        return result


def _response_is_error(response: Any) -> bool:
    """Return whether the tool result itself is marked ``isError``.

    Args:
        response (Any): Raw MCP tool response.

    Returns:
        bool: True when ``isError`` is set. False when it is absent, false,
        or unreadable, so a formatter failure on a successful result still
        exits 0.
    """
    try:
        return bool(getattr(response, "isError", False))
    except Exception:
        return False


def is_error_output(output: str) -> bool:
    """Return whether an MCP command result should exit non-zero.

    Args:
        output (str): Text returned by ``cmd_mcp``.

    Returns:
        bool: True for payload errors, SDK errors, and ``isError`` tool
        results. False when the call succeeded, including when formatting
        that successful result failed and the fallback text was returned.
    """
    failed = getattr(output, "failed", None)
    if isinstance(failed, bool):
        return failed
    if output.startswith(_FORMATTER_ERROR_PREFIX):
        return False
    return output.startswith(MCP_ERROR_PREFIX)


def cmd_mcp(
    state: ShellState,
    chat_id: str,
    message_id: str,
    payload: str | None = None,
    file: str | None = None,
    stdin: bool = False,
) -> McpCommandResult:
    """Call an MCP tool with a JSON payload containing name and arguments.

    Args:
        state (ShellState): CLI session holding the user and company ids.
        chat_id (str): Chat the tool call is attributed to.
        message_id (str): Message the tool call is attributed to.
        payload (str | None): Inline JSON payload.
        file (str | None): Path to a JSON payload file.
        stdin (bool): Read the JSON payload from stdin.

    Returns:
        McpCommandResult: Formatted tool output, or an ``mcp:`` error line.
        ``failed`` is true when the call itself failed.
    """
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

    except (ValueError, OSError, unique_sdk.UniqueError) as e:
        return McpCommandResult(f"{MCP_ERROR_PREFIX} {e}", failed=True)

    try:
        formatted = format_mcp_response(response, tool_name=name)
    except Exception as fmt_exc:
        try:
            fallback = json.dumps(dict(response), indent=2, default=str)
        except Exception:
            fallback = repr(response)
        formatted = f"{_FORMATTER_ERROR_PREFIX} ({fmt_exc}); raw response:\n{fallback}"
    call_failed = _response_is_error(response)

    server_name = _server_name_from_tool(name) or getattr(response, "mcpServerId", None)
    sources_block = record_mcp_citations(
        response,
        tool_name=name,
        server_name=server_name,
        unique_dir=workspace_unique_dir(),
        formatted_text=formatted,
        reference_mapping=state.mcp_tool_reference_mappings.get(name),
    )
    # Sources block FIRST: large outputs get spilled/truncated tail-first by
    # the agent harness, and a trailing block is what partial reads miss.
    if sources_block:
        formatted = sources_block + "\n\n" + formatted
    return McpCommandResult(formatted, failed=call_failed)
