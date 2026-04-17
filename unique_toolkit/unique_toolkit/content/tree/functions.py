"""Pure functions behind the content-tree view.

These helpers are decoupled from :class:`~unique_toolkit.content.tree.service.ContentTree`
so that other callers (scripts, notebooks, ad-hoc tooling) can compose the same
listing + scope-id-resolution logic without constructing a service instance.

- :func:`get_all_content_infos_async` — paginated fetch of every visible
  :class:`~unique_toolkit.content.schemas.ContentInfo`.
- :func:`translate_scope_id_async` / :func:`translate_scope_ids_async` —
  resolve scope ids (folder ids) to their display names, concurrently.
- :func:`extract_scope_ids_from_content_infos` — collect every scope id
  referenced by ``folderIdPath`` metadata.
- :func:`resolve_visible_file_paths_core` — the composition of the above,
  returning ``(content_info, [folder, ..., filename])`` rows.
- :func:`format_path_trie` — render a :class:`PathTrieNode` as a ``tree(1)``-style
  multi-line string.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from unique_toolkit.content.functions import (
    get_content_info_async,
    get_folder_info_async,
)
from unique_toolkit.content.schemas import ContentInfo, PaginatedContentInfos
from unique_toolkit.content.tree.schemas import PathTrieNode

_LOGGER = logging.getLogger(f"toolkit.content.tree.{__name__}")


def serialize_filter(metadata_filter: dict[str, Any] | None) -> str:
    """Serialize a filter dict to a stable, hashable cache key."""
    try:
        return json.dumps(metadata_filter, sort_keys=True, default=str)
    except TypeError:
        return repr(metadata_filter)


async def get_all_content_infos_async(
    user_id: str,
    company_id: str,
    *,
    metadata_filter: dict[str, Any] | None = None,
    step_size: int = 100,
    max_concurrent_requests: int = 10,
) -> list[ContentInfo]:
    """Fetch every :class:`ContentInfo` visible to the caller using parallel pagination.

    The API caps each response at 100 items, so this helper first asks for the
    total count and then fetches all pages concurrently, bounded by
    ``max_concurrent_requests`` to avoid rate-limiting or connection exhaustion.

    Args:
        user_id: Confidential user id of the caller.
        company_id: Confidential company id of the caller.
        metadata_filter: Optional UniqueQL metadata filter.
        step_size: Page size (max 100).
        max_concurrent_requests: Upper bound on concurrent page fetches.

    Returns:
        All content infos visible to ``user_id`` in ``company_id``.
    """
    first_page = await get_content_info_async(
        user_id=user_id,
        company_id=company_id,
        metadata_filter=metadata_filter,
        take=1,
    )
    total_count = first_page.total_count

    semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _fetch_page(skip: int) -> PaginatedContentInfos:
        async with semaphore:
            return await get_content_info_async(
                user_id=user_id,
                company_id=company_id,
                metadata_filter=metadata_filter,
                skip=skip,
                take=step_size,
            )

    results: list[PaginatedContentInfos | BaseException] = await asyncio.gather(
        *[_fetch_page(i) for i in range(0, total_count, step_size)],
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, BaseException):
            _LOGGER.error("Error fetching paginated content infos", exc_info=result)

    return [
        content_info
        for result in results
        if not isinstance(result, BaseException)
        for content_info in result.content_infos
    ]


async def translate_scope_id_async(
    user_id: str,
    company_id: str,
    scope_id: str,
) -> str | None:
    """Resolve a single ``scope_id`` to a folder name.

    Returns ``None`` (and logs a warning) if the folder lookup fails, so callers
    can batch-resolve ids without a single missing folder aborting the whole
    operation.
    """
    try:
        folder_info = await get_folder_info_async(
            user_id=user_id,
            company_id=company_id,
            scope_id=scope_id,
        )
        return folder_info.name
    except Exception as e:
        _LOGGER.warning(f"Could not resolve folder for scope_id {scope_id}", exc_info=e)
        return None


async def translate_scope_ids_batch(
    translate_one: Callable[[str], Awaitable[str | None]],
    scope_ids: set[str],
    *,
    max_concurrent_requests: int = 25,
) -> dict[str, str]:
    """Resolve many scope ids concurrently, honoring ``max_concurrent_requests``."""
    scope_id_list = list(scope_ids)
    semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _resolve(sid: str) -> str | None:
        async with semaphore:
            return await translate_one(sid)

    results = await asyncio.gather(*[_resolve(sid) for sid in scope_id_list])
    return {sid: name for sid, name in zip(scope_id_list, results) if name is not None}


async def translate_scope_ids_async(
    user_id: str,
    company_id: str,
    scope_ids: set[str],
    *,
    max_concurrent_requests: int = 25,
) -> dict[str, str]:
    """Batch version of :func:`translate_scope_id_async` bound to one caller."""

    async def _translate_one(sid: str) -> str | None:
        return await translate_scope_id_async(
            user_id=user_id, company_id=company_id, scope_id=sid
        )

    return await translate_scope_ids_batch(
        _translate_one,
        scope_ids,
        max_concurrent_requests=max_concurrent_requests,
    )


def extract_scope_ids_from_content_infos(content_infos: list[ContentInfo]) -> set[str]:
    """Collect unique scope ids from ``folderIdPath`` metadata (same rules as legacy API)."""
    scope_ids: set[str] = set()
    for content_info in content_infos:
        if (
            content_info.metadata
            and (folder_id_path := content_info.metadata.get("folderIdPath"))
            is not None
            and isinstance(folder_id_path, str)
        ):
            scope_ids.update(
                sid
                for sid in folder_id_path.replace("uniquepathid://", "").split("/")
                if sid
            )
    return scope_ids


async def resolve_visible_file_paths_core(
    user_id: str,
    company_id: str,
    *,
    metadata_filter: dict[str, Any] | None,
    max_concurrent_scope_lookups: int = 25,
) -> list[tuple[ContentInfo, list[str]]]:
    """List visible content and map each ``folderIdPath`` to folder-name segments."""
    content_infos = await get_all_content_infos_async(
        user_id=user_id,
        company_id=company_id,
        metadata_filter=metadata_filter,
    )
    scope_ids = extract_scope_ids_from_content_infos(content_infos)
    scope_id_to_folder_name = await translate_scope_ids_async(
        user_id=user_id,
        company_id=company_id,
        scope_ids=scope_ids,
        max_concurrent_requests=max_concurrent_scope_lookups,
    )

    resolved: list[tuple[ContentInfo, list[str]]] = []
    for content_info in content_infos:
        if (
            content_info.metadata
            and (folder_id_path := content_info.metadata.get("folderIdPath"))
            is not None
            and isinstance(folder_id_path, str)
        ):
            file_path = [
                scope_id_to_folder_name.get(sid, sid)
                for sid in folder_id_path.replace("uniquepathid://", "").split("/")
                if sid
            ]
        else:
            file_path = ["_no_folder_path"]

        file_path.append(content_info.key)
        resolved.append((content_info, file_path))
    return resolved


def build_trie_from_resolved_paths(
    resolved: list[tuple[ContentInfo, list[str]]],
) -> PathTrieNode:
    """Insert each ``(content, [dir, ..., filename])`` pair into a trie."""
    root = PathTrieNode()
    for _content_info, segments in resolved:
        if not segments:
            continue
        *dirs, filename = segments
        node = root
        for part in dirs:
            if part not in node.children:
                node.children[part] = PathTrieNode()
            node = node.children[part]
        node.files.append(filename)
    for node in root.walk_trie_nodes():
        node.files = sorted(set(node.files))
    return root


def format_path_trie(root: PathTrieNode, *, max_depth: int | None = None) -> str:
    """Render *root* with UTF-8 box drawing (like ``tree``)."""
    lines = root.format_trie_walk(prefix="", depth=0, max_depth=max_depth, lines=None)
    return "\n".join(lines)
