"""Search command: combined search with folder/metadata filters."""

from __future__ import annotations

from typing import Any

import unique_sdk
from unique_sdk import UQLCombinator, UQLOperator

from unique_sdk.cli.formatting import format_search_results
from unique_sdk.cli.state import ShellState

DEFAULT_LIMIT = 200


def _build_metadata_filter(
    folder_scope_id: str | None,
    extra_metadata: list[tuple[str, str]] | None,
) -> dict[str, Any] | None:
    """Build a UniqueQL metadata filter from folder scope and key=value pairs."""
    conditions: list[dict[str, Any]] = []

    if folder_scope_id:
        conditions.append({
            "path": ["folderIdPath"],
            "operator": UQLOperator.CONTAINS,
            "value": f"uniquepathid://{folder_scope_id}",
        })

    if extra_metadata:
        for key, value in extra_metadata:
            conditions.append({
                "path": [key],
                "operator": UQLOperator.EQUALS,
                "value": value,
            })

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


def cmd_search(
    state: ShellState,
    query: str,
    folder: str | None = None,
    metadata: list[tuple[str, str]] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> str:
    """Execute a combined search with optional folder and metadata filters."""
    try:
        folder_scope_id: str | None = None
        if folder:
            folder_scope_id = _resolve_folder_to_scope_id(state, folder)
        elif state.scope_id:
            folder_scope_id = state.scope_id

        scope_ids: list[str] | None = None
        if folder_scope_id:
            scope_ids = [folder_scope_id]

        metadata_filter = _build_metadata_filter(folder_scope_id, metadata)

        search_params: dict[str, Any] = {
            "searchString": query,
            "searchType": "COMBINED",
            "limit": limit,
        }
        if scope_ids:
            search_params["scopeIds"] = scope_ids
        if metadata_filter:
            search_params["metaDataFilter"] = metadata_filter

        results = unique_sdk.Search.create(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **search_params,
        )

        return format_search_results(results)

    except (ValueError, unique_sdk.APIError) as e:
        return f"search: {e}"
