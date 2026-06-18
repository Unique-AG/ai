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

# File extensions with no inherent pagination. Passing ``--pages`` for these is
# meaningless — the whole file is the citeable unit. PDFs and PPTX (slides) are
# paginated; unknown/other extensions (and bare content IDs) are left untouched
# so we only emit the targeted error when we can detect the format confidently.
_NON_PAGINATED_SUFFIXES = frozenset(
    {
        ".xlsx",
        ".xls",
        ".csv",
        ".txt",
        ".md",
        ".html",
        ".htm",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
        ".tiff",
        ".tif",
    }
)


def _is_non_paginated(filename: str) -> bool:
    """True when ``filename`` has a known extension that carries no page numbers."""
    return Path(filename).suffix.lower() in _NON_PAGINATED_SUFFIXES


# Canonical reading-method values declared via ``--read-method``. They record
# the *representation* of the source the agent actually read so the runner can
# reconstruct the matching ground truth for a hallucination check:
# - ``text``    — page/document text (e.g. pdftotext, PyMuPDF get_text,
#                 MarkItDown conversion).
# - ``vision``  — the page/slide rendered as an image and read with vision.
# - ``indexed`` — content read through the platform index (unique-cli
#                 read/search), i.e. existing chunks.
READ_METHODS = ("text", "vision", "indexed")

# Convenience aliases accepted from the agent and normalized to canonical values.
_READ_METHOD_ALIASES = {
    "pdftotext": "text",
    "pymupdf": "text",
    "fitz": "text",
    "mupdf": "text",
    "pdfminer": "text",
    "markitdown": "text",
    "image": "vision",
    "ocr": "vision",
    "render": "vision",
    "read": "indexed",
    "search": "indexed",
}


def _normalize_read_method(read_method: str | None) -> str | None:
    """Normalize a ``--read-method`` value to a canonical one, or None if invalid.

    Case-insensitive, with a small alias map. Returns None for missing or
    unrecognized values so callers can fail closed with a clear message.
    """
    if not read_method or not read_method.strip():
        return None
    candidate = read_method.strip().lower()
    candidate = _READ_METHOD_ALIASES.get(candidate, candidate)
    return candidate if candidate in READ_METHODS else None


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
    1. If name_or_id starts with "cont_", return it directly.
    2. Check .unique/chat-files.json for a matching filename (exact or basename).
    3. Fall back to KB resolution via _resolve_content_id.
    """
    if name_or_id.startswith("cont_"):
        return name_or_id, name_or_id

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
    read_method: str | None,
) -> str:
    """Declare citations for a file's pages.

    Writes entries to .unique/file-refs.jsonl and returns [filesourceN]
    markers for the agent to use inline. ``read_method`` records how the cited
    page text was read (one of :data:`READ_METHODS`); it is mandatory and
    validated here as defense in depth for callers that bypass the CLI layer.
    """
    canonical_method = _normalize_read_method(read_method)
    if canonical_method is None:
        return (
            f"{CITE_ERROR_PREFIX} --read-method is required and must be one of: "
            f"{', '.join(READ_METHODS)}. Report the method that produced the "
            "text you actually used."
        )

    try:
        content_id, filename = _resolve_content_id_with_manifest(state, name_or_id)
    except Exception as exc:
        return f"{CITE_ERROR_PREFIX} {exc}"

    if pages and pages.strip() and _is_non_paginated(filename):
        suffix = Path(filename).suffix.lower()
        return (
            f"{CITE_ERROR_PREFIX} {filename} is non-paginated ({suffix} files "
            "have no pages) — omit --pages to cite the whole file."
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

            # Track the source number and the read method already recorded for
            # each (contentId, page) so we can dedup and flag method conflicts.
            existing_keys: dict[tuple[str, int], tuple[int, str]] = {}
            for entry in existing:
                key = (entry.get("contentId", ""), entry.get("page", 0))
                existing_keys[key] = (
                    entry.get("sourceNumber", 0),
                    entry.get("readMethod", ""),
                )

            next_source_number = (
                max(sn for sn, _ in existing_keys.values()) + 1 if existing_keys else 1
            )

            output_lines: list[str] = []
            for page in page_list:
                key = (content_id, page)
                if key in existing_keys:
                    sn, prior_method = existing_keys[key]
                    # A page is grounded by a single representation. If the agent
                    # re-cites it with a different method, keep the first and say
                    # so explicitly rather than silently dropping the new method.
                    if prior_method and prior_method != canonical_method:
                        note = (
                            f"already declared with --read-method "
                            f"{prior_method}; keeping it (one read-method per "
                            "page — issue a separate cite for a different page)"
                        )
                    else:
                        note = "already declared"
                    output_lines.append(
                        f"[filesource{sn}] -> {filename} page {page} ({note})"
                    )
                    continue

                entry = {
                    "sourceNumber": next_source_number,
                    "contentId": content_id,
                    "filename": filename,
                    "page": page,
                    "readMethod": canonical_method,
                }
                _append_turn_refs_manifest_entry(refs_log_path, entry)
                output_lines.append(
                    f"[filesource{next_source_number}] -> {filename} page {page}"
                )
                existing_keys[key] = (next_source_number, canonical_method)
                next_source_number += 1

    except UnsafeRefsLogPathError as exc:
        return f"{CITE_ERROR_PREFIX} {exc}"

    return "\n".join(output_lines)
