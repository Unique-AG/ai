"""Cite command: declare file page citations without extracting text."""

from __future__ import annotations

import json
from pathlib import Path

from unique_sdk.cli.commands._citation_manifest import (
    UnsafeRefsLogPathError,
    _append_turn_refs_manifest_entry,
    _locked_turn_refs_manifest,
    _read_turn_refs_manifest,
)
from unique_sdk.cli.commands.files import _resolve_content_id
from unique_sdk.cli.state import ShellState

CITE_ERROR_PREFIX = "cite:"

_FILE_REFS_LOG_RELATIVE_PATH = Path(".unique") / "file-refs.jsonl"
_FILE_REFS_LOCK_FILENAME = "file-refs.lock"
_CHAT_FILES_MANIFEST = Path(".unique") / "chat-files.json"


_MAX_PAGES_PER_CALL = 500


def _parse_pages(pages: str | None) -> list[int]:
    """Parse '3-7' or '1,3,5' into a list of 1-based page numbers.

    Returns [0] (whole-file) when pages is None or empty.
    Returns [] on invalid input (triggers error in caller).
    """
    if not pages or not pages.strip():
        return [0]
    selected: list[int] = []
    for part in pages.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            bounds = part.split("-", 1)
            start_s, end_s = bounds[0].strip(), bounds[1].strip()
            if not start_s.isdecimal() or not end_s.isdecimal():
                return []
            start, end = int(start_s), int(end_s)
            if start < 1 or end < start or (end - start + 1) > _MAX_PAGES_PER_CALL:
                return []
            selected.extend(range(start, end + 1))
        else:
            if not part.isdecimal() or int(part) < 1:
                return []
            selected.append(int(part))
    if not selected:
        return []
    if len(set(selected)) > _MAX_PAGES_PER_CALL:
        return []
    return sorted(set(selected))


def _resolve_content_id_with_manifest(
    state: ShellState, name_or_id: str
) -> tuple[str, str]:
    """Resolve a filename/content_id checking the chat-files manifest first.

    Resolution order:
    1. If name_or_id starts with "cont_", resolve its title via the API so the
       citation renders with the document filename, not the opaque id.
    2. Check .unique/chat-files.json for a matching filename (exact or basename).
    3. Fall back to KB resolution via _resolve_content_id.
    """
    if name_or_id.startswith("cont_"):
        return name_or_id, state.resolve_content_title(name_or_id)

    manifest_path = Path.cwd() / _CHAT_FILES_MANIFEST
    if manifest_path.is_file():
        try:
            manifest: dict[str, str] = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            manifest = {}

        basename = Path(name_or_id).name
        content_id = manifest.get(name_or_id) or manifest.get(basename)
        if content_id:
            return content_id, basename

    return _resolve_content_id(state, name_or_id)


def cmd_cite_file(
    state: ShellState,
    name_or_id: str,
    pages: str | None,
) -> str:
    """Declare citations for a file's pages.

    Writes entries to .unique/file-refs.jsonl and returns [filesourceN]
    markers for the agent to use inline.
    """
    try:
        content_id, filename = _resolve_content_id_with_manifest(state, name_or_id)
    except Exception as exc:
        return f"{CITE_ERROR_PREFIX} {exc}"

    # When a per-message KB scope filter is active (e.g. an Agentic Table
    # column's scope_rules), don't let the agent cite documents outside it.
    # Chat-attached files are exempt — is_content_within_workspace allows them.
    # Static-scope (no per-message filter) cite behaviour is left unchanged.
    if (
        state.workspace_metadata_filter is not None
        and not state.is_content_within_workspace(content_id)
    ):
        return (
            f"{CITE_ERROR_PREFIX} permission denied: {content_id} is outside your "
            f"task scope ({state.scope_denial_hint()}). Only cite documents within "
            "that scope or files attached to this chat."
        )

    page_list = _parse_pages(pages)
    if not page_list:
        return f"{CITE_ERROR_PREFIX} invalid --pages value"

    refs_log_path = Path.cwd() / _FILE_REFS_LOG_RELATIVE_PATH

    try:
        with _locked_turn_refs_manifest(
            refs_log_path, lock_filename=_FILE_REFS_LOCK_FILENAME
        ):
            existing = _read_turn_refs_manifest(refs_log_path)

            existing_keys: dict[tuple[str, int], int] = {}
            for entry in existing:
                key = (entry.get("contentId", ""), entry.get("page", 0))
                existing_keys[key] = entry.get("sourceNumber", 0)

            next_source_number = max(existing_keys.values()) + 1 if existing_keys else 1

            output_lines: list[str] = []
            for page in page_list:
                key = (content_id, page)
                if key in existing_keys:
                    sn = existing_keys[key]
                    output_lines.append(
                        f"[filesource{sn}] -> {filename} page {page} (already declared)"
                    )
                    continue

                entry = {
                    "sourceNumber": next_source_number,
                    "contentId": content_id,
                    "filename": filename,
                    "page": page,
                }
                _append_turn_refs_manifest_entry(refs_log_path, entry)
                output_lines.append(
                    f"[filesource{next_source_number}] -> {filename} page {page}"
                )
                existing_keys[key] = next_source_number
                next_source_number += 1

    except UnsafeRefsLogPathError as exc:
        return f"{CITE_ERROR_PREFIX} {exc}"

    return "\n".join(output_lines)


def is_error_output(output: str) -> bool:
    """Return ``True`` when *output* is an error message from ``cmd_cite_file``.

    Lets the one-shot dispatcher exit non-zero (so shell ``&&`` chains stop) on
    any cite failure — invalid pages, missing file, or an out-of-scope denial.
    Mirrors ``read.is_error_output``.
    """
    return output.startswith(CITE_ERROR_PREFIX)
