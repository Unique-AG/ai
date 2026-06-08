"""Read command: retrieve all indexed text chunks for a known content ID.

Calls ``Content.search(where={"id": {"equals": cont_id}})`` — a direct
Postgres lookup that returns every indexed chunk for the document in one
request, no vector search involved.

Use this when you already know the ``cont_*`` ID (e.g. from a prior ``ls``
or ``unique-cli search`` result) and want to read the full document text.
For discovery or query-based retrieval use ``unique-cli search`` instead.

Pass ``from_page``/``to_page`` to read only part of a long document by page
range; chunks are filtered client-side on the ``startPage``/``endPage`` the
platform already returns, so no ingestion changes are required.
"""

from __future__ import annotations

from typing import Any

import unique_sdk
from unique_sdk.cli.state import ShellState

READ_ERROR_PREFIX = "read:"


def _chunk_in_page_range(
    chunk: dict[str, Any],
    from_page: int | None,
    to_page: int | None,
) -> bool:
    """Return True if *chunk* overlaps the requested ``[from_page, to_page]`` span.

    A chunk covers ``startPage``..``endPage`` inclusive. With page-based chunking
    these are equal (one chunk per page); otherwise a single chunk can span
    several pages, so we keep any chunk that *overlaps* the requested range
    rather than one fully contained in it. Chunks without page numbers are
    excluded, since they cannot be placed on a page. ``from_page``/``to_page``
    that are ``None`` act as open bounds.
    """
    start: int | None = chunk.get("startPage")
    end: int | None = chunk.get("endPage")
    if start is None:
        start = end
    if end is None:
        end = start
    if start is None or end is None:
        return False

    low = from_page if from_page is not None else start
    high = to_page if to_page is not None else end
    return start <= high and end >= low


def _format_requested_range(from_page: int | None, to_page: int | None) -> str:
    """Human-readable label for a requested page range (for messages)."""
    if from_page is not None and to_page is not None:
        return str(from_page) if from_page == to_page else f"{from_page}-{to_page}"
    if from_page is not None:
        return f"{from_page}+"
    return f"up to {to_page}"


def cmd_read(
    state: ShellState,
    cont_id: str,
    from_page: int | None = None,
    to_page: int | None = None,
    max_chars: int | None = None,
) -> str:
    """Return indexed text chunks for *cont_id* as plain text.

    Args:
        state: Shell state carrying user/company credentials.
        cont_id: A content ID (``cont_...``) to retrieve.
        from_page: First page to include (inclusive). ``None`` = open start.
        to_page: Last page to include (inclusive). ``None`` = open end.
        max_chars: Truncate the returned text to at most this many characters.

    Returns:
        A formatted string of chunks, or an error message prefixed with
        ``read:``.

    When ``from_page``/``to_page`` are given, chunks are filtered to those that
    overlap the requested pages. The page numbers come from ingestion; nothing
    needs to change there. A chunk spanning pages 2-4 is returned for any range
    touching 2-4, so the text may include a little from neighbouring pages.
    """
    if not cont_id.startswith("cont_"):
        return f"{READ_ERROR_PREFIX} expected a content ID starting with 'cont_', got: {cont_id!r}"

    if from_page is not None and to_page is not None and from_page > to_page:
        return f"{READ_ERROR_PREFIX} invalid page range ({from_page} > {to_page})"

    # Enforce the same .unique-search.json workspace boundary as search/ls/rm.
    # Content.search has no scopeIds param, so we guard by owner scope before
    # the point-lookup — matching rm/mv, not search's API-level scopeIds filter.
    if not state.is_content_within_workspace(cont_id):
        return f"{READ_ERROR_PREFIX} permission denied (outside workspace scope)"

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

    if from_page is not None or to_page is not None:
        sorted_chunks = [
            c for c in sorted_chunks if _chunk_in_page_range(c, from_page, to_page)
        ]
        if not sorted_chunks:
            page_range = _format_requested_range(from_page, to_page)
            return (
                f"Content: {title} ({cont_id})\n"
                f"No indexed chunks found in page range {page_range}. The document "
                "may not have page numbers (e.g. plain text/markdown) or spans a "
                "different range — read without a page range to see all text."
            )

    lines: list[str] = [
        f"Content: {title} ({cont_id}) — {len(sorted_chunks)} chunk(s)\n"
    ]
    for chunk in sorted_chunks:
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        start = chunk.get("startPage")
        end = chunk.get("endPage")
        if start is not None or end is not None:
            page_start = start if start is not None else end
            page_end = end if end is not None else start
            if page_start is not None and page_end is not None:
                page_ref = (
                    f"[p.{page_start}]"
                    if page_start == page_end
                    else f"[p.{page_start}-{page_end}]"
                )
                lines.append(f"{page_ref} {text}")
            else:
                lines.append(text)
        else:
            lines.append(text)

    output = "\n\n".join(lines)
    if max_chars is not None and len(output) > max_chars:
        if from_page is not None or to_page is not None:
            hint = "narrow the page range or raise --max-chars to see more"
        else:
            hint = "use a page range (--page/--from-page/--to-page) or raise --max-chars to see more"
        output = f"{output[:max_chars]}\n... [truncated at {max_chars} chars; {hint}]"
    return output


def is_error_output(output: str) -> bool:
    """Return ``True`` when *output* is an error message from ``cmd_read``."""
    return output.startswith(READ_ERROR_PREFIX)
