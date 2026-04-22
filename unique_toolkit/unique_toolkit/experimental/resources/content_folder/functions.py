"""Low-level calls to ``unique_sdk.Folder``.

In the Unique API, a knowledge-base folder is a **content scope**; its primary key is
``scopeId``. This module uses ``scope_id`` in Python signatures and passes it through
as ``scopeId`` to the SDK. ``parent_scope_id`` maps to ``parentScopeId`` when creating
under an existing folder.

Folder **creation** supports two shapes that match :class:`unique_sdk.Folder.CreateParams`:

1. **Absolute paths** — full paths from the knowledge-base root, e.g. ``"/Reports/Q1"``.
   Sent as ``paths`` in the API.
2. **Under an existing parent** — the parent folder’s **scope id** plus path *segments*
   to create under it, e.g. parent ``scope_abc`` and segments ``["2024", "Q1"]``. Sent as
   ``parentScopeId`` + ``relativePaths`` in the API.

**Private to creator (toolkit default):** When ``private_to_creator`` is true (the default) and
``inherit_access`` is false, after ``create_paths`` the toolkit grants the acting ``user_id``
READ and WRITE on **each** folder returned in ``createdFolders``. This makes the new chain
usable by the creator; it does **not** remove ACL entries the API may add for other principals—
for strict “only this user” guarantees, the backend would need to expose replace/clear ACL or
you must call :func:`delete_access` for unwanted grants when you know them.
"""

from __future__ import annotations

import asyncio
from typing import cast

import unique_sdk

from unique_toolkit.experimental.content_folder.schemas import (
    AccessEntityType,
    AccessType,
    CreatedFolder,
    DeleteResult,
    FolderDetail,
    FolderInfo,
    ScopeAccess,
)


def create(
    user_id: str,
    company_id: str,
    *,
    absolute_paths: list[str] | None = None,
    parent_scope_id: str | None = None,
    relative_path_segments: list[str] | None = None,
    inherit_access: bool = False,
    private_to_creator: bool = True,
) -> list[CreatedFolder]:
    """Create folders using exactly one of the two API modes (see module docstring).

    Args:
        user_id: Acting user (SDK requirement).
        company_id: Owning company (SDK requirement).
        absolute_paths: Full paths from root; mutually exclusive with parent mode.
        parent_scope_id: Scope id of the parent folder; use with ``relative_path_segments``.
        relative_path_segments: Path segments under that parent (not full paths).
        inherit_access: When true, new folders copy access rules from the parent.
        private_to_creator: When true (default) and ``inherit_access`` is false, grant the
            acting user READ+WRITE on every created folder. Ignored when ``inherit_access`` is true.

    Raises:
        ValueError: If neither mode is specified correctly or both modes are mixed.
    """
    params = _build_create_params(
        absolute_paths=absolute_paths,
        parent_scope_id=parent_scope_id,
        relative_path_segments=relative_path_segments,
        inherit_access=inherit_access,
    )

    result = unique_sdk.Folder.create_paths(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    created = [
        CreatedFolder.model_validate(f, by_alias=True, by_name=True)
        for f in result["createdFolders"]
    ]
    if private_to_creator and not inherit_access and created:
        _grant_creator_access_on_created_folders(
            user_id=user_id,
            company_id=company_id,
            created=created,
        )
    return created


async def create_async(
    user_id: str,
    company_id: str,
    *,
    absolute_paths: list[str] | None = None,
    parent_scope_id: str | None = None,
    relative_path_segments: list[str] | None = None,
    inherit_access: bool = False,
    private_to_creator: bool = True,
) -> list[CreatedFolder]:
    """Async variant of :func:`create`."""
    params = _build_create_params(
        absolute_paths=absolute_paths,
        parent_scope_id=parent_scope_id,
        relative_path_segments=relative_path_segments,
        inherit_access=inherit_access,
    )

    result = await unique_sdk.Folder.create_paths_async(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    created = [
        CreatedFolder.model_validate(f, by_alias=True, by_name=True)
        for f in result["createdFolders"]
    ]
    if private_to_creator and not inherit_access and created:
        await _grant_creator_access_on_created_folders_async(
            user_id=user_id,
            company_id=company_id,
            created=created,
        )
    return created


def _build_create_params(
    *,
    absolute_paths: list[str] | None,
    parent_scope_id: str | None,
    relative_path_segments: list[str] | None,
    inherit_access: bool,
) -> unique_sdk.Folder.CreateParams:
    has_absolute = absolute_paths is not None
    has_parent = parent_scope_id is not None or relative_path_segments is not None

    if has_absolute and has_parent:
        raise ValueError(
            "Choose one creation style: either absolute_paths=[...] "
            "or parent_scope_id=... with relative_path_segments=[...], not both."
        )

    if has_absolute:
        if not absolute_paths:
            raise ValueError("absolute_paths must be a non-empty list when provided.")
        params: unique_sdk.Folder.CreateParams = unique_sdk.Folder.CreateParams(
            paths=absolute_paths
        )
    elif parent_scope_id is not None and relative_path_segments is not None:
        if not relative_path_segments:
            raise ValueError(
                "relative_path_segments must be a non-empty list when creating under a parent."
            )
        params = unique_sdk.Folder.CreateParams(
            parentScopeId=parent_scope_id,
            relativePaths=relative_path_segments,
        )
    else:
        raise ValueError(
            "Provide absolute_paths=[...] for full paths from the root, "
            "or parent_scope_id=... together with relative_path_segments=[...] "
            "to create nested folders under an existing folder."
        )

    if inherit_access:
        params["inheritAccess"] = True
    return params


def creator_scope_access_grants(user_id: str) -> list[ScopeAccess]:
    """READ and WRITE for the acting user (used for creator-private folders)."""
    return [
        ScopeAccess(
            entity_id=user_id,
            type=AccessType.READ,
            entity_type=AccessEntityType.USER,
        ),
        ScopeAccess(
            entity_id=user_id,
            type=AccessType.WRITE,
            entity_type=AccessEntityType.USER,
        ),
    ]


def _grant_creator_access_on_created_folders(
    *,
    user_id: str,
    company_id: str,
    created: list[CreatedFolder],
) -> None:
    grants = creator_scope_access_grants(user_id)
    for folder in created:
        create_access(
            user_id=user_id,
            company_id=company_id,
            scope_id=folder.id,
            scope_accesses=grants,
            apply_to_sub_scopes=False,
        )


async def _grant_creator_access_on_created_folders_async(
    *,
    user_id: str,
    company_id: str,
    created: list[CreatedFolder],
) -> None:
    grants = creator_scope_access_grants(user_id)
    await asyncio.gather(
        *[
            create_access_async(
                user_id=user_id,
                company_id=company_id,
                scope_id=folder.id,
                scope_accesses=grants,
                apply_to_sub_scopes=False,
            )
            for folder in created
        ]
    )


# ── Read ──────────────────────────────────────────────────────────────────────


def read(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
) -> FolderInfo:
    """Load folder metadata by ``scope_id`` or ``folder_path`` (exactly one required)."""
    params = _build_get_params(scope_id=scope_id, folder_path=folder_path)
    info = unique_sdk.Folder.get_info(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    return FolderInfo.model_validate(info, by_alias=True, by_name=True)


async def read_async(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
) -> FolderInfo:
    """Async variant of :func:`read`."""
    params = _build_get_params(scope_id=scope_id, folder_path=folder_path)
    info = await unique_sdk.Folder.get_info_async(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    return FolderInfo.model_validate(info, by_alias=True, by_name=True)


# ── Access management ─────────────────────────────────────────────────────────


def _build_add_access_params(
    *,
    scope_id: str | None,
    folder_path: str | None,
    scope_accesses: list[ScopeAccess],
    apply_to_sub_scopes: bool,
) -> unique_sdk.Folder.AddAccessParams:
    scope_id, folder_path = _validate_scope_address(
        scope_id=scope_id, folder_path=folder_path
    )
    params = unique_sdk.Folder.AddAccessParams(
        scopeAccesses=_to_sdk_scope_accesses(scope_accesses),
        applyToSubScopes=apply_to_sub_scopes,
    )
    if scope_id is not None:
        params["scopeId"] = scope_id
    if folder_path is not None:
        params["folderPath"] = folder_path
    return params


def _build_remove_access_params(
    *,
    scope_id: str | None,
    folder_path: str | None,
    scope_accesses: list[ScopeAccess],
    apply_to_sub_scopes: bool,
) -> unique_sdk.Folder.RemoveAccessParams:
    scope_id, folder_path = _validate_scope_address(
        scope_id=scope_id, folder_path=folder_path
    )
    params = unique_sdk.Folder.RemoveAccessParams(
        scopeAccesses=_to_sdk_scope_accesses(scope_accesses),
        applyToSubScopes=apply_to_sub_scopes,
    )
    if scope_id is not None:
        params["scopeId"] = scope_id
    if folder_path is not None:
        params["folderPath"] = folder_path
    return params


def create_access(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
    scope_accesses: list[ScopeAccess],
    apply_to_sub_scopes: bool = False,
) -> FolderDetail:
    """Grant READ/WRITE to users or groups (address folder by ``scope_id`` or ``folder_path``)."""
    params = _build_add_access_params(
        scope_id=scope_id,
        folder_path=folder_path,
        scope_accesses=scope_accesses,
        apply_to_sub_scopes=apply_to_sub_scopes,
    )

    result = unique_sdk.Folder.add_access(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    return FolderDetail.model_validate(result, by_alias=True, by_name=True)


async def create_access_async(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
    scope_accesses: list[ScopeAccess],
    apply_to_sub_scopes: bool = False,
) -> FolderDetail:
    """Async variant of :func:`create_access`."""
    params = _build_add_access_params(
        scope_id=scope_id,
        folder_path=folder_path,
        scope_accesses=scope_accesses,
        apply_to_sub_scopes=apply_to_sub_scopes,
    )

    result = await unique_sdk.Folder.add_access_async(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    return FolderDetail.model_validate(result, by_alias=True, by_name=True)


def delete_access(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
    scope_accesses: list[ScopeAccess],
    apply_to_sub_scopes: bool = False,
) -> FolderDetail:
    """Revoke access entries (address folder by ``scope_id`` or ``folder_path``)."""
    params = _build_remove_access_params(
        scope_id=scope_id,
        folder_path=folder_path,
        scope_accesses=scope_accesses,
        apply_to_sub_scopes=apply_to_sub_scopes,
    )

    result = unique_sdk.Folder.remove_access(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    return FolderDetail.model_validate(result, by_alias=True, by_name=True)


async def delete_access_async(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
    scope_accesses: list[ScopeAccess],
    apply_to_sub_scopes: bool = False,
) -> FolderDetail:
    """Async variant of :func:`delete_access`."""
    params = _build_remove_access_params(
        scope_id=scope_id,
        folder_path=folder_path,
        scope_accesses=scope_accesses,
        apply_to_sub_scopes=apply_to_sub_scopes,
    )

    result = await unique_sdk.Folder.remove_access_async(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    return FolderDetail.model_validate(result, by_alias=True, by_name=True)


# ── Delete ────────────────────────────────────────────────────────────────────


def delete(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
    recursive: bool = False,
) -> DeleteResult:
    """Delete a folder by ``scope_id`` or ``folder_path`` (exactly one required).

    Args:
        user_id: Acting user (SDK requirement).
        company_id: Owning company (SDK requirement).
        scope_id: Scope id of the folder to delete.
        folder_path: Absolute path from the knowledge-base root.
        recursive: When true, request recursive deletion per API semantics.
    """
    params = _build_delete_params(
        scope_id=scope_id,
        folder_path=folder_path,
        recursive=recursive,
    )
    raw = unique_sdk.Folder.delete(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    return DeleteResult.model_validate(raw, by_alias=True, by_name=True)


async def delete_async(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
    recursive: bool = False,
) -> DeleteResult:
    """Async variant of :func:`delete`."""
    params = _build_delete_params(
        scope_id=scope_id,
        folder_path=folder_path,
        recursive=recursive,
    )
    raw = await unique_sdk.Folder.delete_async(
        user_id=user_id,
        company_id=company_id,
        **params,
    )
    return DeleteResult.model_validate(raw, by_alias=True, by_name=True)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_sdk_scope_accesses(
    scope_accesses: list[ScopeAccess],
) -> list[unique_sdk.Folder.ScopeAccess]:
    return cast(
        list[unique_sdk.Folder.ScopeAccess],
        [a.model_dump(by_alias=True, exclude_none=True) for a in scope_accesses],
    )


def _validate_scope_address(
    *,
    scope_id: str | None,
    folder_path: str | None,
) -> tuple[str | None, str | None]:
    """Require exactly one of ``scope_id`` or ``folder_path``."""
    if scope_id is None and folder_path is None:
        raise ValueError("Pass exactly one of scope_id or folder_path.")
    if scope_id is not None and folder_path is not None:
        raise ValueError("Pass only one of scope_id or folder_path, not both.")
    return scope_id, folder_path


def _build_get_params(
    *,
    scope_id: str | None,
    folder_path: str | None,
) -> unique_sdk.Folder.GetParams:
    scope_id, folder_path = _validate_scope_address(
        scope_id=scope_id, folder_path=folder_path
    )
    params = unique_sdk.Folder.GetParams()
    if scope_id is not None:
        params["scopeId"] = scope_id
    if folder_path is not None:
        params["folderPath"] = folder_path
    return params


def _build_delete_params(
    *,
    scope_id: str | None,
    folder_path: str | None,
    recursive: bool,
) -> unique_sdk.Folder.DeleteFolderParams:
    scope_id, folder_path = _validate_scope_address(
        scope_id=scope_id, folder_path=folder_path
    )
    params: unique_sdk.Folder.DeleteFolderParams = {}
    if scope_id is not None:
        params["scopeId"] = scope_id
    if folder_path is not None:
        params["folderPath"] = folder_path
    if recursive:
        params["recursive"] = True
    return params
