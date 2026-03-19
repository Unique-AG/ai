"""Tabular output formatting for ls, search results, and file info."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _format_size(byte_size: int | None) -> str:
    if byte_size is None:
        return "-"
    if byte_size < 1024:
        return f"{byte_size} B"
    if byte_size < 1024 * 1024:
        return f"{byte_size / 1024:.1f} KB"
    if byte_size < 1024 * 1024 * 1024:
        return f"{byte_size / (1024 * 1024):.1f} MB"
    return f"{byte_size / (1024 * 1024 * 1024):.1f} GB"


def _format_date(iso_str: str | None) -> str:
    if not iso_str:
        return "-"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return iso_str[:16] if len(iso_str) >= 16 else iso_str


def _pad_columns(rows: list[list[str]]) -> list[str]:
    """Pad columns to align output."""
    if not rows:
        return []
    col_count = max(len(r) for r in rows)
    widths = [0] * col_count
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    lines: list[str] = []
    for row in rows:
        parts: list[str] = []
        for i, cell in enumerate(row):
            if i == len(row) - 1:
                parts.append(cell)
            else:
                parts.append(cell.ljust(widths[i]))
        lines.append("  ".join(parts))
    return lines


def format_ls(
    folders: list[dict[str, Any]],
    files: list[dict[str, Any]],
) -> str:
    """Format ls output: folders first, then files, with type/name/id/size/date columns."""
    rows: list[list[str]] = []
    for f in folders:
        name = f.get("name", "?")
        fid = f.get("id", "?")
        updated = _format_date(f.get("updatedAt"))
        rows.append(["DIR", f"{name}/", fid, "", updated])

    for c in files:
        title = c.get("title") or c.get("key") or "?"
        cid = c.get("id", "?")
        size = _format_size(c.get("byteSize"))
        updated = _format_date(c.get("updatedAt"))
        rows.append(["FILE", title, cid, size, updated])

    if not rows:
        return "(empty)"

    return "\n".join(_pad_columns(rows))


def format_search_results(results: list[Any]) -> str:
    """Format search results with index, title, pages, and text snippet."""
    if not results:
        return "No results found."

    lines: list[str] = [f"Found {len(results)} result(s):\n"]
    for i, r in enumerate(results, 1):
        title = getattr(r, "title", None) or getattr(r, "key", None) or "?"
        content_id = getattr(r, "id", "?")
        start_page = getattr(r, "startPage", None)
        end_page = getattr(r, "endPage", None)

        page_info = ""
        if start_page is not None:
            if end_page is not None and end_page != start_page:
                page_info = f" (p.{start_page}-{end_page})"
            else:
                page_info = f" (p.{start_page})"

        text = getattr(r, "text", "") or ""
        snippet = text[:120].replace("\n", " ").strip()
        if len(text) > 120:
            snippet += "..."

        lines.append(f"  {i:3d}. {title}{page_info}  [{content_id}]")
        if snippet:
            lines.append(f"       {snippet}")

    return "\n".join(lines)


def format_content_info(info: dict[str, Any]) -> str:
    """Format a single content info record."""
    rows = [
        ["ID:", info.get("id", "?")],
        ["Title:", info.get("title") or info.get("key") or "?"],
        ["MIME:", info.get("mimeType", "?")],
        ["Size:", _format_size(info.get("byteSize"))],
        ["Owner:", info.get("ownerId", "?")],
        ["Created:", _format_date(info.get("createdAt"))],
        ["Updated:", _format_date(info.get("updatedAt"))],
    ]
    return "\n".join(_pad_columns(rows))


def format_folder_info(info: dict[str, Any]) -> str:
    """Format a single folder info record."""
    rows = [
        ["ID:", info.get("id", "?")],
        ["Name:", info.get("name", "?")],
        ["Parent:", info.get("parentId") or "(root)"],
        ["Created:", _format_date(info.get("createdAt"))],
        ["Updated:", _format_date(info.get("updatedAt"))],
    ]
    return "\n".join(_pad_columns(rows))
