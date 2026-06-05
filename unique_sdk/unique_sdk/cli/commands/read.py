"""Read command: retrieve all indexed text chunks for a known content ID.

Calls ``Content.search(where={"id": {"equals": cont_id}})`` — a direct
Postgres lookup that returns every indexed chunk for the document in one
request, no vector search involved.

Use this when you already know the ``cont_*`` ID (e.g. from a prior ``ls``
or ``unique-cli search`` result) and want to read the full document text.
For discovery or query-based retrieval use ``unique-cli search`` instead.
"""

from __future__ import annotations

import unique_sdk
from unique_sdk.cli.state import ShellState

READ_ERROR_PREFIX = "read:"


def cmd_read(state: ShellState, cont_id: str) -> str:
    """Return all indexed text chunks for *cont_id* as plain text.

    Args:
        state: Shell state carrying user/company credentials.
        cont_id: A content ID (``cont_...``) to retrieve.

    Returns:
        A formatted string of chunks, or an error message prefixed with
        ``read:``.
    """
    if not cont_id.startswith("cont_"):
        return f"{READ_ERROR_PREFIX} expected a content ID starting with 'cont_', got: {cont_id!r}"

    try:
        results = unique_sdk.Content.search(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            where={"id": {"equals": cont_id}},
        )
    except unique_sdk.APIError as e:
        return f"{READ_ERROR_PREFIX} {e}"

    if not results:
        return f"{READ_ERROR_PREFIX} no content found for ID: {cont_id}"

    content = results[0]
    title = getattr(content, "title", None) or getattr(content, "key", None) or cont_id
    chunks = getattr(content, "chunks", None) or []

    if not chunks:
        return (
            f"Content: {title} ({cont_id})\n"
            "No indexed chunks found — the document may still be ingesting or ingestion failed."
        )

    sorted_chunks = sorted(chunks, key=lambda c: c.get("order") or 0)

    lines: list[str] = [
        f"Content: {title} ({cont_id}) — {len(sorted_chunks)} chunk(s)\n"
    ]
    for chunk in sorted_chunks:
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        start = chunk.get("startPage")
        end = chunk.get("endPage")
        if start and end:
            page_ref = f"[p.{start}]" if start == end else f"[p.{start}-{end}]"
            lines.append(f"{page_ref} {text}")
        else:
            lines.append(text)

    return "\n\n".join(lines)


def is_error_output(output: str) -> bool:
    """Return ``True`` when *output* is an error message from ``cmd_read``."""
    return output.startswith(READ_ERROR_PREFIX)
