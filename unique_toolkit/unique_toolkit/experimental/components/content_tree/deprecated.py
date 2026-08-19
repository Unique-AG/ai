"""Deprecated full-catalog ContentTree helpers.

These functions paginate **every** visible :class:`ContentInfo` and then
resolve ``folderIdPath`` segments. That does not honor ``max_depth`` or
``timeout`` and is too slow on a large knowledge base.

Use :func:`~unique_toolkit.experimental.components.content_tree.functions.walk_visible_paths_via_folders_async`
or :meth:`~unique_toolkit.experimental.components.content_tree.service.ContentTree.resolve_visible_file_paths_via_folders_async`
instead (``Folder.get_infos`` walk).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import PurePosixPath
from typing import Any

from typing_extensions import deprecated

from unique_toolkit.content.functions import (
    get_content_info_async,
    get_folder_info_async,
    get_folder_path_async,
)
from unique_toolkit.content.schemas import ContentInfo, PaginatedContentInfos

_LOGGER = logging.getLogger(f"toolkit.experimental.components.content_tree.{__name__}")

_DEPRECATION = (
    "Loading every ContentInfo is deprecated. Use "
    "walk_visible_paths_via_folders_async or "
    "ContentTree.resolve_visible_file_paths_via_folders_async "
    "(Folder.get_infos walk with max_depth and timeout)."
)


async def _get_all_content_infos_async(
    user_id: str,
    company_id: str,
    *,
    metadata_filter: dict[str, Any] | None = None,
    step_size: int = 100,
    max_concurrent_requests: int = 10,
) -> list[ContentInfo]:
    """Fetch every :class:`ContentInfo` visible to the caller using parallel pagination.

    The API caps each response at 100 items, so this helper fetches the first
    page at ``step_size`` (which already includes ``totalCount``) and then the
    remaining pages concurrently, bounded by ``max_concurrent_requests``.

    Args:
        user_id (str): Confidential user id of the caller.
        company_id (str): Confidential company id of the caller.
        metadata_filter (dict[str, Any] | None): Optional UniqueQL metadata filter.
        step_size (int): Page size (max 100).
        max_concurrent_requests (int): Upper bound on concurrent page fetches.

    Returns:
        list[ContentInfo]: All content infos visible to ``user_id`` in
        ``company_id``.
    """
    first_page = await get_content_info_async(
        user_id=user_id,
        company_id=company_id,
        metadata_filter=metadata_filter,
        skip=0,
        take=step_size,
    )
    total_count = first_page.total_count
    content_infos: list[ContentInfo] = list(first_page.content_infos)

    remaining_skips = list(range(step_size, total_count, step_size))
    if not remaining_skips:
        return content_infos

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
        *[_fetch_page(skip) for skip in remaining_skips],
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, BaseException):
            _LOGGER.error("Error fetching paginated content infos", exc_info=result)
            continue
        content_infos.extend(result.content_infos)
    return content_infos


@deprecated(_DEPRECATION)
async def get_all_content_infos_async(
    user_id: str,
    company_id: str,
    *,
    metadata_filter: dict[str, Any] | None = None,
    step_size: int = 100,
    max_concurrent_requests: int = 10,
) -> list[ContentInfo]:
    """Fetch every :class:`ContentInfo` visible to the caller using parallel pagination.

    Args:
        user_id (str): Confidential user id of the caller.
        company_id (str): Confidential company id of the caller.
        metadata_filter (dict[str, Any] | None): Optional UniqueQL metadata filter.
        step_size (int): Page size (max 100).
        max_concurrent_requests (int): Upper bound on concurrent page fetches.

    Returns:
        list[ContentInfo]: All content infos visible to ``user_id`` in
        ``company_id``.
    """
    return await _get_all_content_infos_async(
        user_id,
        company_id,
        metadata_filter=metadata_filter,
        step_size=step_size,
        max_concurrent_requests=max_concurrent_requests,
    )


@deprecated(_DEPRECATION)
async def translate_scope_id_async(
    user_id: str,
    company_id: str,
    scope_id: str,
) -> str | None:
    """Resolve a single ``scope_id`` to a folder name.

    Returns ``None`` if the folder lookup fails (logged at debug; callers fall
    back to the raw ``scope_id``), so batch resolution is not aborted by a
    single miss.
    """
    try:
        folder_info = await get_folder_info_async(
            user_id=user_id,
            company_id=company_id,
            scope_id=scope_id,
        )
        return folder_info.name
    except Exception as e:
        _LOGGER.debug("Could not resolve folder for scope_id %s", scope_id, exc_info=e)
        return None


@deprecated(_DEPRECATION)
async def translate_scope_ids_batch[T](
    translate_one: Callable[[str], Awaitable[T | None]],
    scope_ids: set[str],
    *,
    max_concurrent_requests: int = 25,
) -> dict[str, T]:
    """Resolve many scope ids concurrently, honoring ``max_concurrent_requests``.

    Failed lookups (``None``) are omitted so callers can fall back per id.
    """
    scope_id_list = list(scope_ids)
    semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _resolve(sid: str) -> T | None:
        async with semaphore:
            return await translate_one(sid)

    results = await asyncio.gather(*[_resolve(sid) for sid in scope_id_list])
    return {
        sid: value
        for sid, value in zip(scope_id_list, results, strict=True)
        if value is not None
    }


@deprecated(_DEPRECATION)
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


def _scope_ids_from_folder_id_path(folder_id_path: str) -> list[str]:
    """Split ``uniquepathid://id1/id2`` (or a bare ``id1/id2``) into scope ids."""
    return [
        sid for sid in folder_id_path.replace("uniquepathid://", "").split("/") if sid
    ]


def _folder_id_path_scope_ids(content_info: ContentInfo) -> list[str] | None:
    """Return ``folderIdPath`` segments, or ``None`` if the field is absent/invalid."""
    if (
        content_info.metadata
        and (folder_id_path := content_info.metadata.get("folderIdPath")) is not None
        and isinstance(folder_id_path, str)
    ):
        return _scope_ids_from_folder_id_path(folder_id_path)
    return None


def _named_segments_from_folder_path(folder_path: str) -> list[str]:
    """Split ``/Company/Reports`` into ``['Company', 'Reports']``."""
    return [part for part in folder_path.split("/") if part]


@deprecated(_DEPRECATION)
async def translate_folder_path_async(
    user_id: str,
    company_id: str,
    scope_id: str,
) -> list[str] | None:
    """Resolve a folder id to named path segments via ``GET /folder/{id}/path``.

    Returns ``None`` if the lookup fails (logged at debug; callers fall back
    to raw scope ids), so batch resolution is not aborted by a single miss.

    Args:
        user_id (str): Confidential user id of the caller.
        company_id (str): Confidential company id of the caller.
        scope_id (str): Leaf folder scope id to resolve.

    Returns:
        list[str] | None: Path segments, or ``None`` on lookup failure.
    """
    try:
        folder_path = await get_folder_path_async(
            user_id=user_id,
            company_id=company_id,
            scope_id=scope_id,
        )
        return _named_segments_from_folder_path(folder_path)
    except Exception as e:
        _LOGGER.debug(
            "Could not resolve folder path for scope_id %s", scope_id, exc_info=e
        )
        return None


@deprecated(_DEPRECATION)
async def translate_folder_paths_async(
    user_id: str,
    company_id: str,
    scope_ids: set[str],
    *,
    max_concurrent_requests: int = 25,
) -> dict[str, list[str]]:
    """Batch version of :func:`translate_folder_path_async` bound to one caller.

    Args:
        user_id (str): Confidential user id of the caller.
        company_id (str): Confidential company id of the caller.
        scope_ids (set[str]): Leaf folder ids to resolve.
        max_concurrent_requests (int): Upper bound on concurrent path fetches.

    Returns:
        dict[str, list[str]]: Mapping from scope id to named path segments.
            Failed lookups are omitted.
    """

    async def _translate_one(sid: str) -> list[str] | None:
        return await translate_folder_path_async(
            user_id=user_id, company_id=company_id, scope_id=sid
        )

    return await translate_scope_ids_batch(
        _translate_one,
        scope_ids,
        max_concurrent_requests=max_concurrent_requests,
    )


@deprecated(_DEPRECATION)
def extract_scope_ids_from_content_infos(content_infos: list[ContentInfo]) -> set[str]:
    """Collect unique scope ids from ``folderIdPath`` metadata (same rules as legacy API)."""
    scope_ids: set[str] = set()
    for content_info in content_infos:
        segments = _folder_id_path_scope_ids(content_info)
        if segments is not None:
            scope_ids.update(segments)
    return scope_ids


@deprecated(_DEPRECATION)
def extract_leaf_scope_ids_from_content_infos(
    content_infos: list[ContentInfo],
) -> set[str]:
    """Collect unique *leaf* folder ids (last ``folderIdPath`` segment).

    Files in the same directory share a leaf id, so resolving only these ids
    via :func:`translate_folder_paths_async` is enough to name every path.

    Args:
        content_infos (list[ContentInfo]): Content rows to scan.

    Returns:
        set[str]: Distinct leaf scope ids. Empty when nothing has a folder path.
    """
    leaf_ids: set[str] = set()
    for content_info in content_infos:
        segments = _folder_id_path_scope_ids(content_info)
        if segments:
            leaf_ids.add(segments[-1])
    return leaf_ids


@deprecated(_DEPRECATION)
async def resolve_visible_file_paths_core(
    user_id: str,
    company_id: str,
    *,
    metadata_filter: dict[str, Any] | None,
    max_concurrent_scope_lookups: int = 25,
) -> list[tuple[ContentInfo, PurePosixPath]]:
    """List visible content and map each ``folderIdPath`` to a POSIX path.

    Folder names come from ``GET /folder/{leafId}/path`` once per unique parent
    folder, not from one ``get_info`` per ancestor id.

    Args:
        user_id (str): Confidential user id of the caller.
        company_id (str): Confidential company id of the caller.
        metadata_filter (dict[str, Any] | None): Optional UniqueQL filter.
        max_concurrent_scope_lookups (int): Concurrency for leaf-path fetches.

    Returns:
        list[tuple[ContentInfo, PurePosixPath]]: Each row is
        ``(content_info, path)``. Unresolvable folders keep the raw scope ids;
        content without ``folderIdPath`` uses ``_no_folder_path``.
    """
    content_infos = await get_all_content_infos_async(
        user_id=user_id,
        company_id=company_id,
        metadata_filter=metadata_filter,
        max_concurrent_requests=50,
    )
    leaf_ids = extract_leaf_scope_ids_from_content_infos(content_infos)
    leaf_to_segments = await translate_folder_paths_async(
        user_id=user_id,
        company_id=company_id,
        scope_ids=leaf_ids,
        max_concurrent_requests=max_concurrent_scope_lookups,
    )

    resolved: list[tuple[ContentInfo, PurePosixPath]] = []
    for content_info in content_infos:
        scope_ids = _folder_id_path_scope_ids(content_info)
        if scope_ids is None:
            folders = PurePosixPath("_no_folder_path")
        elif scope_ids and (named := leaf_to_segments.get(scope_ids[-1])) is not None:
            folders = PurePosixPath(*named) if named else PurePosixPath()
        else:
            folders = PurePosixPath(*scope_ids) if scope_ids else PurePosixPath()

        resolved.append((content_info, folders / content_info.key))
    return resolved
