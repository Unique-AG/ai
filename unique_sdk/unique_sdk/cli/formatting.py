"""Tabular output formatting for ls, search results, file info, scheduled tasks, elicitations, and MCP responses."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any

from unique_sdk.api_resources._content import Content
from unique_sdk.api_resources._folder import Folder

if TYPE_CHECKING:
    from unique_sdk.api_resources._agentic_table import (
        AgenticTableCell,
        AgenticTableSheet,
    )
    from unique_sdk.api_resources._mcp import MCP
    from unique_sdk.api_resources._scheduled_task import ScheduledTask


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


def _snippet(text: str | None, limit: int = 80) -> str:
    """Collapse *text* to a single-line snippet no longer than *limit* chars."""
    collapsed = (text or "").replace("\n", " ").strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit] + "..."


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


def format_scheduled_task(task: ScheduledTask) -> str:
    """Format a single scheduled task as a key-value display."""
    enabled_str = "yes" if getattr(task, "enabled", False) else "no"
    rows = [
        ["ID:", getattr(task, "id", "?")],
        ["Cron:", getattr(task, "cronExpression", "?")],
        [
            "Assistant:",
            getattr(task, "assistantName", None) or getattr(task, "assistantId", "?"),
        ],
        ["Assistant ID:", getattr(task, "assistantId", "?")],
        ["Chat ID:", getattr(task, "chatId", None) or "(new chat each run)"],
        ["Prompt:", getattr(task, "prompt", "?")],
        ["Enabled:", enabled_str],
        ["Last run:", _format_date(getattr(task, "lastRunAt", None))],
        ["Created:", _format_date(getattr(task, "createdAt", None))],
        ["Updated:", _format_date(getattr(task, "updatedAt", None))],
    ]
    return "\n".join(_pad_columns(rows))


def format_scheduled_tasks(tasks: list[ScheduledTask]) -> str:
    """Format a list of scheduled tasks as a table."""
    if not tasks:
        return "No scheduled tasks found."

    rows: list[list[str]] = []
    for t in tasks:
        task_id = getattr(t, "id", "?")
        cron = getattr(t, "cronExpression", "?")
        enabled = "on" if getattr(t, "enabled", False) else "off"
        assistant = getattr(t, "assistantName", None) or getattr(t, "assistantId", "?")
        prompt = getattr(t, "prompt", "")
        snippet = prompt[:60].replace("\n", " ").strip()
        if len(prompt) > 60:
            snippet += "..."
        last_run = _format_date(getattr(t, "lastRunAt", None))
        rows.append([enabled, cron, assistant, snippet, task_id, last_run])

    header = ["STATUS", "CRON", "ASSISTANT", "PROMPT", "ID", "LAST RUN"]
    lines = [f"{len(tasks)} scheduled task(s):\n"]
    all_rows = [header] + rows
    lines.extend(_pad_columns(all_rows))
    return "\n".join(lines)


def format_elicitation(elicitation: Mapping[str, Any]) -> str:
    """Format a single elicitation request for terminal display.

    Includes the response content inline when the elicitation has been
    answered, which is what agents primarily need when consuming the output
    of ``elicit wait`` / ``elicit ask``.
    """
    response_content = elicitation.get("responseContent")
    response_json = (
        json.dumps(response_content, ensure_ascii=False)
        if response_content is not None
        else "(none)"
    )
    schema = elicitation.get("schema")
    schema_json = json.dumps(schema, ensure_ascii=False) if schema is not None else "-"
    metadata = elicitation.get("metadata")
    metadata_json = (
        json.dumps(metadata, ensure_ascii=False) if metadata is not None else "-"
    )

    rows = [
        ["ID:", elicitation.get("id", "?")],
        ["Status:", elicitation.get("status", "?")],
        ["Mode:", elicitation.get("mode", "?")],
        ["Source:", elicitation.get("source", "?")],
        ["Tool:", elicitation.get("toolName") or "-"],
        ["Message:", elicitation.get("message", "")],
        ["Schema:", schema_json],
        ["URL:", elicitation.get("url") or "-"],
        ["Chat:", elicitation.get("chatId") or "-"],
        ["Message ID:", elicitation.get("messageId") or "-"],
        ["External ID:", elicitation.get("externalElicitationId") or "-"],
        ["Metadata:", metadata_json],
        ["Response:", response_json],
        ["Responded:", _format_date(elicitation.get("respondedAt"))],
        ["Expires:", _format_date(elicitation.get("expiresAt"))],
        ["Created:", _format_date(elicitation.get("createdAt"))],
        ["Updated:", _format_date(elicitation.get("updatedAt"))],
    ]
    return "\n".join(_pad_columns(rows))


def format_pending_elicitations(elicitations: Sequence[Mapping[str, Any]]) -> str:
    """Format the list of pending elicitations as a compact table."""
    if not elicitations:
        return "No pending elicitations."

    header = ["STATUS", "MODE", "TOOL", "MESSAGE", "ID", "EXPIRES"]
    rows: list[list[str]] = [header]
    for item in elicitations:
        status = str(item.get("status", "?"))
        mode = str(item.get("mode", "?"))
        tool = str(item.get("toolName") or "-")
        message = str(item.get("message") or "")
        snippet = message[:60].replace("\n", " ").strip()
        if len(message) > 60:
            snippet += "..."
        elicitation_id = str(item.get("id", "?"))
        expires = _format_date(item.get("expiresAt"))
        rows.append([status, mode, tool, snippet, elicitation_id, expires])

    lines = [f"{len(elicitations)} pending elicitation(s):\n"]
    lines.extend(_pad_columns(rows))
    return "\n".join(lines)


def format_elicitation_response(
    result: Mapping[str, Any],
    elicitation_id: str,
    action: str,
) -> str:
    """Format the result of ``respond_to_elicitation``."""
    success = bool(result.get("success"))
    status = "OK" if success else "FAILED"
    rows = [
        ["Elicitation:", elicitation_id],
        ["Action:", action],
        ["Result:", status],
    ]
    detail = result.get("message")
    if detail:
        rows.append(["Detail:", str(detail)])
    return "\n".join(_pad_columns(rows))


def format_mcp_response(response: MCP, *, tool_name: str | None = None) -> str:
    """Format an MCP tool call response for terminal display.

    The MCP spec only guarantees ``content`` in a successful ``CallToolResult``.
    ``isError``, ``name``, and ``mcpServerId`` are optional in practice (some
    Unique backend builds omit them on success), so we access them defensively
    and fall back to the caller-supplied tool name when the server omits it.
    """
    is_error = bool(getattr(response, "isError", False))
    name = getattr(response, "name", None) or tool_name or "<unknown-tool>"
    server_id = getattr(response, "mcpServerId", None) or "<unknown-server>"
    content = getattr(response, "content", None) or []

    error_tag = " (ERROR)" if is_error else ""
    header = f"MCP tool call: {name}{error_tag}"
    server_line = f"Server: {server_id}"

    lines: list[str] = [header, server_line, ""]

    for item in content:
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
            link_name = item.get("name") or "?"
            uri = item.get("uri") or "?"
            desc = item.get("description") or ""
            lines.append(f"[resource_link] {link_name}: {uri}")
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


def format_agentic_table_sheet(
    sheet: AgenticTableSheet,
    *,
    include_cells: bool = False,
) -> str:
    """Format an Agentic Table sheet summary as a key-value display.

    Sheet-level metadata and cell values are only rendered when the caller
    requested them (``includeSheetMetadata`` / ``includeCells``); absent
    sections are skipped rather than shown empty.
    """
    rows = [
        ["Sheet:", sheet.get("name", "?")],
        ["ID:", sheet.get("sheetId", "?")],
        ["State:", str(sheet.get("state", "?"))],
    ]
    if "magicTableRowCount" in sheet:
        rows.append(["Rows:", str(sheet.get("magicTableRowCount"))])
    if sheet.get("chatId"):
        rows.append(["Chat:", sheet["chatId"]])
    rows.append(["Created by:", sheet.get("createdBy", "?")])
    rows.append(["Created:", _format_date(sheet.get("createdAt"))])
    lines = _pad_columns(rows)

    metadata = sheet.get("magicTableSheetMetadata") or []
    if metadata:
        lines.append("")
        lines.append("Metadata:")
        meta_rows = [
            [f"  {entry.get('key', '?')}:", entry.get("value", "")]
            for entry in metadata
        ]
        lines.extend(_pad_columns(meta_rows))

    cells = sheet.get("magicTableCells") or []
    if include_cells and cells:
        lines.append("")
        lines.append(f"Cells ({len(cells)}):")
        cell_rows: list[list[str]] = [["ROW", "COL", "TEXT"]]
        for cell in cells:
            cell_rows.append(
                [
                    str(cell.get("rowOrder", "?")),
                    str(cell.get("columnOrder", "?")),
                    _snippet(cell.get("text", "")),
                ]
            )
        lines.extend(_pad_columns(cell_rows))

    return "\n".join(lines)


def format_agentic_table_cell(cell: AgenticTableCell) -> str:
    """Format a single Agentic Table cell (text + lock state)."""
    rows = [
        ["Sheet:", cell.get("sheetId", "?")],
        ["Row:", str(cell.get("rowOrder", "?"))],
        ["Column:", str(cell.get("columnOrder", "?"))],
        ["Locked:", "yes" if cell.get("rowLocked") else "no"],
    ]
    lines = _pad_columns(rows)
    lines.append("")
    lines.append("Text:")
    lines.append(cell.get("text", ""))
    return "\n".join(lines)


def format_agentic_table_cell_history(cell: AgenticTableCell) -> str:
    """Format an Agentic Table cell's log/edit history newest-to-oldest.

    Each entry shows its timestamp, actor, optional source message id, and the
    logged text (the actor + reason recorded by writes). The order is whatever
    the API returns; no client-side sorting is imposed.
    """
    entries = cell.get("logEntries") or []
    row = cell.get("rowOrder", "?")
    col = cell.get("columnOrder", "?")
    plural = "entry" if len(entries) == 1 else "entries"
    header = f"Cell history (row {row}, col {col}) — {len(entries)} {plural}"
    if not entries:
        return f"{header}\n(no log entries)"

    lines = [header, ""]
    for entry in entries:
        actor = entry.get("actorType", "?")
        when = _format_date(entry.get("createdAt"))
        message_id = entry.get("messageId")
        suffix = f"  [{message_id}]" if message_id else ""
        lines.append(f"- {when}  {actor}{suffix}")
        text = (entry.get("text") or "").strip()
        for text_line in text.splitlines():
            lines.append(f"    {text_line}")
    return "\n".join(lines)
