"""Tabular output formatting for ls, search results, file info, and MCP responses."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from unique_sdk.api_resources._content import Content
from unique_sdk.api_resources._folder import Folder

if TYPE_CHECKING:
    from unique_sdk.api_resources._mcp import MCP



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
    folders: list[Folder.FolderInfo],
    files: list[Content.ContentInfo],
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


def format_content_info(info: Content.ContentInfo) -> str:
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


def format_folder_info(info: Folder.FolderInfo) -> str:
    """Format a single folder info record."""
    rows = [
        ["ID:", info.get("id", "?")],
        ["Name:", info.get("name", "?")],
        ["Parent:", info.get("parentId") or "(root)"],
        ["Created:", _format_date(info.get("createdAt"))],
        ["Updated:", _format_date(info.get("updatedAt"))],
    ]
    return "\n".join(_pad_columns(rows))


def format_mcp_response(response: MCP) -> str:
    """Format an MCP tool call response for terminal display."""
    error_tag = " (ERROR)" if response.isError else ""
    header = f"MCP tool call: {response.name}{error_tag}"
    server_line = f"Server: {response.mcpServerId}"

    lines: list[str] = [header, server_line, ""]

    for item in response.content:
        content_type = item.get("type", "unknown")

        if content_type == "text":
            text = item.get("text") or ""
            for text_line in text.splitlines():
                lines.append(f"[text] {text_line}")

        elif content_type == "image":
            mime = item.get("mimeType") or "image/*"
            lines.append(f"[image] ({mime}, base64-encoded data)")

        elif content_type == "audio":
            mime = item.get("mimeType") or "audio/*"
            lines.append(f"[audio] ({mime}, base64-encoded data)")

        elif content_type == "resource_link":
            name = item.get("name") or "?"
            uri = item.get("uri") or "?"
            desc = item.get("description") or ""
            lines.append(f"[resource_link] {name}: {uri}")
            if desc:
                lines.append(f"  {desc}")

        elif content_type == "resource":
            resource = item.get("resource")
            if resource and "text" in resource:
                uri = resource.get("uri", "?")
                lines.append(f"[resource] {uri}")
                for res_line in (resource.get("text") or "").splitlines():
                    lines.append(f"  {res_line}")
            elif resource and "blob" in resource:
                uri = resource.get("uri", "?")
                mime = resource.get("mimeType") or "application/octet-stream"
                lines.append(f"[resource] {uri} ({mime}, base64-encoded)")
            else:
                lines.append("[resource] (empty)")

        else:
            lines.append(f"[{content_type}] (unsupported content type)")

    return "\n".join(lines)
