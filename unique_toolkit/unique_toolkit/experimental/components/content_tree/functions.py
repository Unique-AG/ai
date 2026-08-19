"""Pure functions behind the folder-walk content-tree view.

These helpers are decoupled from :class:`~unique_toolkit.experimental.components.content_tree.service.ContentTree`
so that other callers (scripts, notebooks, ad-hoc tooling) can compose the same
``Folder.get_infos`` walk without constructing a service instance.

- :func:`walk_visible_paths_via_folders_async` — snapshot via recursive
  ``Folder.get_infos`` + ``Content.get_infos(parentId)``. ``max_depth`` stops
  the walk; optional ``timeout`` returns a partial snapshot. Render with
  :meth:`~unique_toolkit.experimental.components.content_tree.schemas.FolderWalkSnapshot.render`.
- :func:`resolve_visible_file_paths_core` — deprecated adapter that returns
  ``list[tuple[ContentInfo, list[str]]]`` from that walk.
- :func:`format_path_trie` — render a :class:`PathTrieNode` as a ``tree(1)``-style
  multi-line string (prefer :meth:`FolderWalkSnapshot.render`).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import PurePosixPath
from typing import Any

import unique_sdk
from typing_extensions import deprecated

from unique_toolkit.content.schemas import BaseFolderInfo, ContentInfo
from unique_toolkit.experimental.components.content_tree.schemas import (
    FolderWalkSnapshot,
    PathTrieNode,
)

__all__ = [
    "build_trie_from_resolved_paths",
    "format_path_trie",
    "resolve_visible_file_paths_core",
    "serialize_filter",
    "walk_visible_paths_via_folders_async",
]

_LOGGER = logging.getLogger(f"toolkit.experimental.components.content_tree.{__name__}")


def serialize_filter(metadata_filter: dict[str, Any] | None) -> str:
    """Serialize a filter dict to a stable, hashable cache key."""
    try:
        return json.dumps(metadata_filter, sort_keys=True, default=str)
    except TypeError:
        return repr(metadata_filter)


def _parse_folder_infos_payload(payload: Any) -> tuple[list[BaseFolderInfo], int]:
    raw = payload.get("folderInfos") or []
    folders = [
        BaseFolderInfo.model_validate(item, by_alias=True, by_name=True) for item in raw
    ]
    total = int(payload.get("totalCount", len(folders)))
    return folders, total


def _parse_content_infos_payload(payload: Any) -> tuple[list[ContentInfo], int]:
    raw = payload.get("contentInfos") or []
    files = [
        ContentInfo.model_validate(item, by_alias=True, by_name=True) for item in raw
    ]
    total = int(payload.get("totalCount", len(files)))
    return files, total


def _propagate_wait_interrupt(result: object) -> None:
    """Re-raise timeout/cancellation so callers can return a partial snapshot."""
    if isinstance(result, (asyncio.CancelledError, TimeoutError)):
        raise result


async def _paginate_parent_listing[T](
    fetch_page: Callable[[int], Awaitable[Any]],
    parse_page: Callable[[Any], tuple[list[T], int]],
    *,
    step_size: int,
    max_concurrent_requests: int,
    on_page: Callable[[list[T]], None] | None = None,
) -> list[T]:
    """Fetch skip=0 at ``step_size``, then remaining pages concurrently.

    ``on_page`` runs after each page so callers can publish partial progress
    before the full listing finishes.
    """
    first_payload = await fetch_page(0)
    items, total_count = parse_page(first_payload)
    if on_page:
        on_page(items)
    remaining_skips = list(range(step_size, total_count, step_size))
    if not remaining_skips:
        return items

    semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _fetch(skip: int) -> list[T]:
        async with semaphore:
            payload = await fetch_page(skip)
            page_items, _total = parse_page(payload)
            if on_page:
                on_page(page_items)
            return page_items

    extra = await asyncio.gather(
        *[_fetch(skip) for skip in remaining_skips],
        return_exceptions=True,
    )
    for page in extra:
        _propagate_wait_interrupt(page)
        if isinstance(page, BaseException):
            _LOGGER.warning("Skipping listing page after fetch error: %s", page)
            continue
        items.extend(page)
    return items


async def _list_direct_children_async(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None,
    metadata_filter: dict[str, Any] | None,
    step_size: int,
    max_concurrent_page_fetches: int,
    on_folders: Callable[[list[BaseFolderInfo]], None] | None = None,
    on_files: Callable[[list[ContentInfo]], None] | None = None,
) -> list[BaseFolderInfo]:
    """Child folders (and files when ``scope_id`` is set) of one parent.

    ``scope_id=None`` is the knowledge-base root. ``Content.get_infos`` without
    ``parentId`` lists the **entire** catalog, so root only fetches folders.
    Files are listed per folder with ``parentId``.
    """
    parent_params: dict[str, Any] = {}
    if scope_id:
        parent_params["parentId"] = scope_id

    async def _folder_page(skip: int) -> Any:
        return await unique_sdk.Folder.get_infos_async(
            user_id=user_id,
            company_id=company_id,
            skip=skip,
            take=step_size,
            **parent_params,
        )

    folders_task = _paginate_parent_listing(
        _folder_page,
        _parse_folder_infos_payload,
        step_size=step_size,
        max_concurrent_requests=max_concurrent_page_fetches,
        on_page=on_folders,
    )
    if not scope_id:
        return await folders_task

    async def _content_page(skip: int) -> Any:
        params = dict(parent_params)
        if metadata_filter:
            params["metadataFilter"] = metadata_filter
        return await unique_sdk.Content.get_infos_async(
            user_id=user_id,
            company_id=company_id,
            skip=skip,
            take=step_size,
            **params,
        )

    folder_result, file_result = await asyncio.gather(
        folders_task,
        _paginate_parent_listing(
            _content_page,
            _parse_content_infos_payload,
            step_size=step_size,
            max_concurrent_requests=max_concurrent_page_fetches,
            on_page=on_files,
        ),
        return_exceptions=True,
    )
    _propagate_wait_interrupt(folder_result)
    _propagate_wait_interrupt(file_result)
    if isinstance(folder_result, BaseException):
        _LOGGER.warning(
            "Skipping folder listing for parent %s: %s", scope_id, folder_result
        )
        return []
    if isinstance(file_result, BaseException):
        _LOGGER.warning(
            "Skipping content listing for parent %s: %s", scope_id, file_result
        )
    return folder_result


async def walk_visible_paths_via_folders_async(
    user_id: str,
    company_id: str,
    *,
    metadata_filter: dict[str, Any] | None = None,
    max_concurrent_scope_lookups: int = 25,
    max_depth: int | None = None,
    max_concurrent_directory_listings: int | None = None,
    step_size: int = 100,
    timeout: float | None = None,
    progress: FolderWalkSnapshot | None = None,
) -> FolderWalkSnapshot:
    """Build a visible-path snapshot by walking ``Folder.get_infos``.

    Each directory is ``Folder.get_infos(parentId)`` plus, when the parent is
    a real folder, ``Content.get_infos(parentId)`` (paginated). The synthetic
    root lists **folders only**: ``Content.get_infos`` without ``parentId``
    dumps every visible file and would stall the walk. Folder names come from
    the folder listing, so this does not call ``get_folder_path``. ``max_depth``
    stops recursion (``tree -L``): depth ``1`` lists only the knowledge-base
    root's children.

    Results are appended to ``progress`` as each listing **page** arrives, so a
    ``timeout`` can return a valid partial tree (``complete=False``) instead of
    raising. Directory listings that already started are shielded so their
    rows still land in the snapshot.

    Args:
        user_id (str): Confidential user id of the caller.
        company_id (str): Confidential company id of the caller.
        metadata_filter (dict[str, Any] | None): Optional UniqueQL filter
            applied to per-folder content listings.
        max_concurrent_scope_lookups (int): Backward-compatible alias for
            ``max_concurrent_directory_listings`` when that argument is omitted.
        max_depth (int | None): Maximum directory depth under the synthetic
            root (``None`` = unlimited).
        max_concurrent_directory_listings (int | None): Bound on concurrent
            directory visits. Defaults to ``max_concurrent_scope_lookups``.
        step_size (int): Page size for folder and content listings (max 100).
        timeout (float | None): Seconds after which further visits are
            cancelled. ``None`` waits for the full walk.
        progress (FolderWalkSnapshot | None): Shared accumulator mutated as
            directories complete. When omitted, a fresh snapshot is used.
            :class:`~unique_toolkit.experimental.components.content_tree.service.ContentTree`
            passes this so a timed-out wait can still read rows while the
            cached walk continues.

    Returns:
        FolderWalkSnapshot: File rows plus every visited folder prefix
        (including empty directories). ``complete`` is ``False`` on timeout.
        The snapshot is also a sequence of ``(content_info, path)`` rows.
    """
    concurrency = (
        max_concurrent_directory_listings
        if max_concurrent_directory_listings is not None
        else max_concurrent_scope_lookups
    )
    acc = progress or FolderWalkSnapshot(files=[], folder_paths=[], complete=False)
    dir_semaphore = asyncio.Semaphore(concurrency)

    async def _list_and_record(
        scope_id: str | None, path: PurePosixPath
    ) -> list[BaseFolderInfo]:
        def _record_folders(page: list[BaseFolderInfo]) -> None:
            acc.folder_paths.extend(path / folder.name for folder in page)

        def _record_files(page: list[ContentInfo]) -> None:
            acc.files.extend((content, path / content.key) for content in page)

        return await _list_direct_children_async(
            user_id,
            company_id,
            scope_id=scope_id,
            metadata_filter=metadata_filter,
            step_size=step_size,
            max_concurrent_page_fetches=10,
            on_folders=_record_folders,
            on_files=_record_files,
        )

    async def _visit(scope_id: str | None, path: PurePosixPath, depth: int) -> None:
        async with dir_semaphore:
            folders = await asyncio.shield(_list_and_record(scope_id, path))
        recurse = max_depth is None or depth + 1 < max_depth
        if recurse and folders:
            child_results = await asyncio.gather(
                *[
                    _visit(folder.id, path / folder.name, depth + 1)
                    for folder in folders
                ],
                return_exceptions=True,
            )
            for folder, result in zip(folders, child_results, strict=True):
                _propagate_wait_interrupt(result)
                if isinstance(result, BaseException):
                    _LOGGER.warning(
                        "Skipping subtree %s (%s): %s",
                        folder.name,
                        folder.id,
                        result,
                    )

    try:
        if timeout is None:
            await _visit(scope_id=None, path=PurePosixPath(), depth=0)
        else:
            async with asyncio.timeout(timeout):
                await _visit(scope_id=None, path=PurePosixPath(), depth=0)
    except TimeoutError:
        acc.complete = False
        return acc.copy(complete=False)

    acc.complete = True
    return acc.copy(complete=True)


@deprecated(
    "Use walk_visible_paths_via_folders_async; it returns FolderWalkSnapshot "
    "with PurePosixPath rows, max_depth, and timeout."
)
async def resolve_visible_file_paths_core(
    user_id: str,
    company_id: str,
    *,
    metadata_filter: dict[str, Any] | None = None,
    max_concurrent_scope_lookups: int = 25,
) -> list[tuple[ContentInfo, list[str]]]:
    """Walk visible folders and return path segments as lists of strings.

    Deprecated wrapper around :func:`walk_visible_paths_via_folders_async`.

    Args:
        user_id (str): Confidential user id of the caller.
        company_id (str): Confidential company id of the caller.
        metadata_filter (dict[str, Any] | None): Optional UniqueQL filter
            applied to per-folder content listings.
        max_concurrent_scope_lookups (int): Bound on concurrent directory
            visits.

    Returns:
        list[tuple[ContentInfo, list[str]]]: Each file paired with POSIX path
        segments (``["Legal", "Contracts", "nda.pdf"]``).
    """
    snapshot = await walk_visible_paths_via_folders_async(
        user_id,
        company_id,
        metadata_filter=metadata_filter,
        max_concurrent_scope_lookups=max_concurrent_scope_lookups,
    )
    return [
        (content_info, [part for part in path.parts if part != "."])
        for content_info, path in snapshot.files
    ]


def build_trie_from_resolved_paths(
    resolved: list[tuple[ContentInfo, PurePosixPath]],
    *,
    extra_folder_paths: list[PurePosixPath] | None = None,
) -> PathTrieNode:
    """Insert each ``(content, path)`` pair into a trie.

    Args:
        resolved (list[tuple[ContentInfo, PurePosixPath]]): File rows.
            ``path.parent`` is the folder, ``path.name`` is the filename.
        extra_folder_paths (list[PurePosixPath] | None): Folder-only prefixes so
            empty directories still appear (used by the folder-walk snapshot).
    """
    return FolderWalkSnapshot(
        files=list(resolved),
        folder_paths=list(extra_folder_paths or []),
    ).to_trie()


def format_path_trie(
    root: PathTrieNode,
    *,
    max_depth: int | None = None,
    show_files: bool = True,
) -> str:
    """Render *root* with UTF-8 box drawing (like ``tree``)."""
    return root.render(max_depth=max_depth, show_files=show_files)
