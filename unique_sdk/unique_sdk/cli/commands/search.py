"""Search command: combined KB search with folder/metadata filters.

Always emits results wrapped in ``<sourceN>...</sourceN>`` blocks and
appends a per-turn ContentChunk-shaped manifest at
``<cwd>/.unique/kb-search-refs.jsonl``. The Swappable Intelligence
runner reads that manifest after the turn to convert ``[sourceN]``
markers in the LLM answer into ``<sup>N</sup>`` footnotes plus
clickable reference chips on the Unique platform.

The manifest format is identical to the legacy ``bundled_skills/kb-search``
``search.py`` from the monorepo — that bundle is being retired in favor of
this CLI command.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import unique_sdk
from unique_sdk import UQLCombinator, UQLOperator
from unique_sdk.cli.commands._citation_manifest import (
    UnsafeRefsLogPathError,
    _append_turn_refs_manifest_entry,
    _locked_turn_refs_manifest,
    _read_turn_refs_manifest,
)
from unique_sdk.cli.state import ShellState

DEFAULT_LIMIT = 200

SEARCH_ERROR_PREFIX = "search:"
UPLOADED_SEARCH_ERROR_PREFIX = "uploaded-search:"

_REFS_LOG_RELATIVE_PATH = Path(".unique") / "kb-search-refs.jsonl"
_LOCK_FILENAME = "kb-search-refs.lock"


def _build_metadata_filter(
    folder_scope_id: str | None,
    extra_metadata: list[tuple[str, str]] | None,
) -> dict[str, Any] | None:
    """Build a UniqueQL metadata filter from folder scope and key=value pairs."""
    conditions: list[dict[str, Any]] = []

    if folder_scope_id:
        conditions.append(
            {
                "path": ["folderIdPath"],
                "operator": UQLOperator.CONTAINS,
                "value": f"uniquepathid://{folder_scope_id}",
            }
        )

    if extra_metadata:
        for key, value in extra_metadata:
            conditions.append(
                {
                    "path": [key],
                    "operator": UQLOperator.EQUALS,
                    "value": value,
                }
            )

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {UQLCombinator.AND: conditions}


def _resolve_folder_to_scope_id(state: ShellState, folder: str) -> str:
    """Resolve a folder path or scope ID to a scope ID."""
    if folder.startswith("scope_"):
        return folder

    if not folder.startswith("/"):
        folder = f"{state.cwd.rstrip('/')}/{folder}"

    info = unique_sdk.Folder.get_info(
        user_id=state.config.user_id,
        company_id=state.config.company_id,
        folderPath=folder,
    )
    scope_id = info.get("id")
    if not scope_id:
        raise ValueError(f"Could not resolve folder: {folder}")
    return scope_id


def _format_source_block(source_number: int, result: Any) -> str:
    """Render one search result as a ``<sourceN>...</sourceN>`` block.

    Mirrors the legacy ``unique_ai`` source format that the Swappable
    Intelligence runner's reference post-processor recognises — ``<sourceN>``
    open/close tags with ``<|document|>``, ``<|page|>``, ``<|info|>``
    sub-sections. The chunk-level metadata (startPage, endPage, url, etc.)
    is captured in full in the JSONL manifest for the runner to consume;
    only the human-relevant bits appear in the on-screen block.
    """
    title = (
        getattr(result, "title", None)
        or getattr(result, "key", None)
        or f"content {getattr(result, 'id', '?')}"
    )
    content_id = getattr(result, "id", "") or ""
    text = getattr(result, "text", "") or ""
    start_page = getattr(result, "startPage", 0) or 0
    end_page = getattr(result, "endPage", 0) or 0

    sections: list[str] = []
    sections.append(f"<|document|>{title}</|document|>")
    if start_page and end_page and start_page > 0 and end_page > 0:
        page_range = (
            str(start_page) if start_page == end_page else f"{start_page}-{end_page}"
        )
        sections.append(f"<|page|>{page_range}</|page|>")
    if content_id:
        sections.append(f"<|info|>{content_id}</|info|>")
    sections.append(text.strip())

    body = "\n".join(sections)
    return f"<source{source_number}>\n{body}\n</source{source_number}>"


def _result_to_chunk_payload(result: Any) -> dict[str, Any]:
    """Convert a ``unique_sdk.Search`` result into a ContentChunk-shaped dict.

    Keys are camelCase aliases of ``unique_toolkit.content.ContentChunk``
    fields so the runner can rehydrate them via
    ``ContentChunk.model_validate(...)``. All keys are emitted (with
    ``None`` when absent) to keep the per-line shape stable.
    """

    def _get(name: str, default: Any = None) -> Any:
        return getattr(result, name, default)

    metadata = _get("metadata")
    return {
        "id": _get("id", "") or "",
        "chunkId": _get("chunkId"),
        "text": _get("text", "") or "",
        "order": _get("order", 0) or 0,
        "key": _get("key"),
        "url": _get("url"),
        "title": _get("title"),
        "startPage": _get("startPage"),
        "endPage": _get("endPage"),
        "metadata": metadata if isinstance(metadata, dict) else None,
        "createdAt": _get("createdAt"),
        "updatedAt": _get("updatedAt"),
    }


def _format_results_with_citations(
    results: list[Any],
    *,
    refs_log_path: Path,
) -> str:
    """Number, format, and persist each result inside one locked critical section.

    Reads the existing manifest under lock so ``sourceN`` numbering keeps
    growing across multiple ``unique-cli search`` invocations within the
    same turn — the runner truncates the manifest at turn start, so the
    first call in a turn starts at 1.
    """
    if not results:
        return "No results found."

    with _locked_turn_refs_manifest(refs_log_path, lock_filename=_LOCK_FILENAME):
        existing_entries = _read_turn_refs_manifest(refs_log_path)
        starting_number = len(existing_entries) + 1

        blocks: list[str] = []
        for offset, result in enumerate(results):
            source_number = starting_number + offset
            blocks.append(_format_source_block(source_number, result))
            _append_turn_refs_manifest_entry(
                refs_log_path,
                _result_to_chunk_payload(result),
            )

    return f"Found {len(results)} result(s):\n\n" + "\n\n".join(blocks)


def cmd_search(
    state: ShellState,
    query: str,
    folder: str | None = None,
    metadata: list[tuple[str, str]] | None = None,
    limit: int = DEFAULT_LIMIT,
    *,
    refs_log_path: Path | None = None,
) -> str:
    """Execute a combined search with optional folder and metadata filters.

    Args:
        state: Shell state carrying user/company credentials and cwd.
        query: Search string.
        folder: Optional folder path, name, or scope ID. Overrides
            ``state.scope_id`` and ``state.workspace_scope_ids``.
        metadata: Optional ``[(key, value), ...]`` metadata filters
            combined with AND.
        limit: Maximum number of results.
        refs_log_path: Override the per-turn citation manifest path —
            for tests; production callers leave this ``None`` so the
            manifest lives at ``<cwd>/.unique/kb-search-refs.jsonl`` and
            the Swappable Intelligence runner can find it.
    """
    try:
        folder_scope_id: str | None = None
        if folder:
            folder_scope_id = _resolve_folder_to_scope_id(state, folder)
        elif state.scope_id and not state.workspace_metadata_filter:
            # The incidental cwd narrows search only when there is no
            # per-message filter. `cd` is not gated by the filter, so an agent
            # can sit in an out-of-scope folder; ANDing that cwd with the task
            # filter would silently return no hits and look like an empty KB
            # rather than a scope mismatch. With a filter active, only an
            # explicit --folder narrows further. See UN-21780.
            folder_scope_id = state.scope_id

        scope_ids: list[str] | None = None
        if folder_scope_id:
            scope_ids = [folder_scope_id]
        elif not folder and state.workspace_scope_ids:
            scope_ids = state.workspace_scope_ids

        metadata_filter = _build_metadata_filter(
            folder_scope_id if metadata else None,
            metadata,
        )

        # A per-message workspace metadata filter (written to
        # .unique-search.json by the Swappable Intelligence runner from an
        # Agentic Table column's scope_rules) replaces the static workspace
        # scope_ids for this call. It can express scopes a flat scopeIds list
        # cannot (recursive folder CONTAINS, contentId IN, boolean trees).
        #
        # It is never *dropped*: an in-session selection (--folder, a cwd
        # scope, --metadata) only narrows further via AND. Yielding to those
        # would let a prompt-controlled `--folder`/`--metadata` argument
        # escape the task boundary entirely. See UN-21780.
        if state.workspace_metadata_filter:
            if metadata_filter:
                metadata_filter = {
                    "and": [state.workspace_metadata_filter, metadata_filter]
                }
            else:
                metadata_filter = state.workspace_metadata_filter
            if folder_scope_id is None:
                # No explicit folder selection: the per-message filter is the
                # authority; don't reapply the broader static workspace
                # scope_ids. An explicit folder stays as scopeIds and the
                # server ANDs it with the metadata filter.
                scope_ids = None

        search_params: dict[str, Any] = {
            "searchString": query,
            "searchType": "COMBINED",
            "limit": limit,
            # An unscoped search must send an explicit ``scopeIds: null``,
            # never omit the key. An absent key reaches node-ingestion as
            # ``undefined`` and is destructure-defaulted to ``[]``, which
            # getScopes treats as "restrict to zero scopes" — an entire-KB
            # search then returns nothing on companies without file-based
            # access. A JSON ``null`` bypasses both the default and the
            # truthy check, matching what unique_toolkit's
            # search_content_chunks sends. See UN-22753.
            "scopeIds": scope_ids or None,
        }
        if metadata_filter:
            search_params["metaDataFilter"] = metadata_filter

        results = unique_sdk.Search.create(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **search_params,
        )

    except (ValueError, unique_sdk.UniqueError) as e:
        return f"{SEARCH_ERROR_PREFIX} {e}"

    log_path = refs_log_path or (Path.cwd() / _REFS_LOG_RELATIVE_PATH)
    try:
        return _format_results_with_citations(results, refs_log_path=log_path)
    except UnsafeRefsLogPathError as exc:
        return f"{SEARCH_ERROR_PREFIX} {exc}"


def cmd_uploaded_search(
    state: ShellState,
    query: str,
    limit: int = DEFAULT_LIMIT,
    *,
    refs_log_path: Path | None = None,
) -> str:
    """Search this task's per-row **uploaded** documents.

    Uploaded files (e.g. an Agentic Table row's attached documents) live
    outside the knowledge-base folder scopes, so the scope-bound
    ``unique-cli search`` cannot return them. This mirrors the platform's
    UploadedSearch tool: a chat-scoped ``Search.create`` (``chatOnly=True``)
    over the owning chat and the selected content ids, both written by the
    Swappable Intelligence runner to ``.unique-uploaded.json``. See UN-21780.

    Results share the same per-turn ``<sourceN>`` manifest as
    ``unique-cli search`` (``_format_results_with_citations`` appends under the
    same lock), so ``[sourceN]`` citation numbering stays continuous across
    both commands within a turn.

    Args:
        state: Shell state carrying user/company credentials and the uploaded
            document scope loaded from ``.unique-uploaded.json``.
        query: Search string.
        limit: Maximum number of results.
        refs_log_path: Override the per-turn citation manifest path — for
            tests; production callers leave this ``None``.
    """
    if not state.uploaded_search_available:
        return (
            f"{UPLOADED_SEARCH_ERROR_PREFIX} no uploaded documents are "
            "available for this task. Use `unique-cli search` for the "
            "knowledge base."
        )

    try:
        search_params: dict[str, Any] = {
            "searchString": query,
            "searchType": "COMBINED",
            "chatOnly": True,
            "limit": limit,
        }
        if state.uploaded_search_chat_id:
            search_params["chatId"] = state.uploaded_search_chat_id
        if state.uploaded_search_content_ids:
            search_params["contentIds"] = state.uploaded_search_content_ids

        results = unique_sdk.Search.create(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **search_params,
        )
    except (ValueError, unique_sdk.UniqueError) as e:
        return f"{UPLOADED_SEARCH_ERROR_PREFIX} {e}"

    log_path = refs_log_path or (Path.cwd() / _REFS_LOG_RELATIVE_PATH)
    try:
        return _format_results_with_citations(results, refs_log_path=log_path)
    except UnsafeRefsLogPathError as exc:
        return f"{UPLOADED_SEARCH_ERROR_PREFIX} {exc}"


def is_error_output(output: str) -> bool:
    """Return ``True`` when ``output`` is a CLI error message.

    Mirrors :func:`unique_sdk.cli.commands.web_search.is_error_output` so
    the Click layer can translate a returned error string into a non-zero
    exit code without changing the existing string-returning contract.
    """
    return output.startswith(SEARCH_ERROR_PREFIX)


def is_uploaded_search_error_output(output: str) -> bool:
    """Return ``True`` when ``output`` is an ``uploaded-search`` error message."""
    return output.startswith(UPLOADED_SEARCH_ERROR_PREFIX)
