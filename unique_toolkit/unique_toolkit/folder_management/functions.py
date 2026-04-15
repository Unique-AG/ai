import logging

import unique_sdk

from unique_toolkit.folder_management.constants import DOMAIN_NAME
from unique_toolkit.folder_management.schemas import (
    CreateFolderStructureResponse,
    DeleteFolderResponse,
    Folder,
    FolderInfo,
    FolderPath,
    FolderScopeAccess,
    PaginatedFolderInfos,
)

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


# ---------------------------------------------------------------------------
# Get folder path
# ---------------------------------------------------------------------------


def get_folder_path(
    user_id: str,
    company_id: str,
    *,
    scope_id: str,
) -> FolderPath:
    """
    Get the complete folder path for a given folder ID.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        scope_id: The folder scope ID.

    Returns:
        FolderPath: The resolved folder path.
    """
    try:
        logger.info("Getting folder path for scope_id=%s", scope_id)
        result = unique_sdk.Folder.get_folder_path(
            user_id=user_id,
            company_id=company_id,
            scope_id=scope_id,
        )
        return FolderPath.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error getting folder path: %s", e)
        raise


async def get_folder_path_async(
    user_id: str,
    company_id: str,
    *,
    scope_id: str,
) -> FolderPath:
    """Async variant of :func:`get_folder_path`."""
    try:
        logger.info("Getting folder path for scope_id=%s", scope_id)
        result = await unique_sdk.Folder.get_folder_path_async(
            user_id=user_id,
            company_id=company_id,
            scope_id=scope_id,
        )
        return FolderPath.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error getting folder path: %s", e)
        raise


# ---------------------------------------------------------------------------
# Get folder info
# ---------------------------------------------------------------------------


def get_folder_info(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
) -> FolderInfo:
    """
    Get info about a single folder by ID or path.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        scope_id: The folder scope ID (mutually exclusive with folder_path).
        folder_path: The folder path (mutually exclusive with scope_id).

    Returns:
        FolderInfo: The folder metadata.
    """
    try:
        logger.info(
            "Getting folder info scope_id=%s folder_path=%s", scope_id, folder_path
        )
        params: dict = {}
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path

        result = unique_sdk.Folder.get_info(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return FolderInfo.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error getting folder info: %s", e)
        raise


async def get_folder_info_async(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
) -> FolderInfo:
    """Async variant of :func:`get_folder_info`."""
    try:
        logger.info(
            "Getting folder info scope_id=%s folder_path=%s", scope_id, folder_path
        )
        params: dict = {}
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path

        result = await unique_sdk.Folder.get_info_async(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return FolderInfo.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error getting folder info: %s", e)
        raise


# ---------------------------------------------------------------------------
# List folders (paginated)
# ---------------------------------------------------------------------------


def list_folders(
    user_id: str,
    company_id: str,
    *,
    parent_id: str | None = None,
    parent_folder_path: str | None = None,
    take: int | None = None,
    skip: int | None = None,
) -> PaginatedFolderInfos:
    """
    List folders under a parent, with pagination. Returns root folders when
    no parent is specified.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        parent_id: Scope ID of the parent folder.
        parent_folder_path: Path of the parent folder (resolved server-side).
        take: Maximum number of folders to return.
        skip: Number of folders to skip.

    Returns:
        PaginatedFolderInfos: Paginated list of folder info objects.
    """
    try:
        logger.info(
            "Listing folders parent_id=%s parent_folder_path=%s",
            parent_id,
            parent_folder_path,
        )
        params: dict = {}
        if parent_id:
            params["parentId"] = parent_id
        if parent_folder_path:
            params["parentFolderPath"] = parent_folder_path
        if take is not None:
            params["take"] = take
        if skip is not None:
            params["skip"] = skip

        result = unique_sdk.Folder.get_infos(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return PaginatedFolderInfos.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error listing folders: %s", e)
        raise


async def list_folders_async(
    user_id: str,
    company_id: str,
    *,
    parent_id: str | None = None,
    parent_folder_path: str | None = None,
    take: int | None = None,
    skip: int | None = None,
) -> PaginatedFolderInfos:
    """Async variant of :func:`list_folders`."""
    try:
        logger.info(
            "Listing folders parent_id=%s parent_folder_path=%s",
            parent_id,
            parent_folder_path,
        )
        params: dict = {}
        if parent_id:
            params["parentId"] = parent_id
        if parent_folder_path:
            params["parentFolderPath"] = parent_folder_path
        if take is not None:
            params["take"] = take
        if skip is not None:
            params["skip"] = skip

        result = await unique_sdk.Folder.get_infos_async(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return PaginatedFolderInfos.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error listing folders: %s", e)
        raise


# ---------------------------------------------------------------------------
# Create folders
# ---------------------------------------------------------------------------


def create_folders(
    user_id: str,
    company_id: str,
    *,
    paths: list[str] | None = None,
    parent_scope_id: str | None = None,
    relative_paths: list[str] | None = None,
    inherit_access: bool = True,
) -> CreateFolderStructureResponse:
    """
    Create one or more folders by path.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        paths: Absolute folder paths to create.
        parent_scope_id: Parent scope ID when using relative paths.
        relative_paths: Relative paths to create under parent_scope_id.
        inherit_access: Whether created folders inherit parent access. Defaults to True.

    Returns:
        CreateFolderStructureResponse: The created folders.
    """
    try:
        logger.info(
            "Creating folders paths=%s relative_paths=%s", paths, relative_paths
        )
        params: dict = {"inheritAccess": inherit_access}
        if paths:
            params["paths"] = paths
        if parent_scope_id:
            params["parentScopeId"] = parent_scope_id
        if relative_paths:
            params["relativePaths"] = relative_paths

        result = unique_sdk.Folder.create_paths(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return CreateFolderStructureResponse.model_validate(
            result, by_alias=True, by_name=True
        )
    except Exception as e:
        logger.error("Error creating folders: %s", e)
        raise


async def create_folders_async(
    user_id: str,
    company_id: str,
    *,
    paths: list[str] | None = None,
    parent_scope_id: str | None = None,
    relative_paths: list[str] | None = None,
    inherit_access: bool = True,
) -> CreateFolderStructureResponse:
    """Async variant of :func:`create_folders`."""
    try:
        logger.info(
            "Creating folders paths=%s relative_paths=%s", paths, relative_paths
        )
        params: dict = {"inheritAccess": inherit_access}
        if paths:
            params["paths"] = paths
        if parent_scope_id:
            params["parentScopeId"] = parent_scope_id
        if relative_paths:
            params["relativePaths"] = relative_paths

        result = await unique_sdk.Folder.create_paths_async(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return CreateFolderStructureResponse.model_validate(
            result, by_alias=True, by_name=True
        )
    except Exception as e:
        logger.error("Error creating folders: %s", e)
        raise


# ---------------------------------------------------------------------------
# Update folder
# ---------------------------------------------------------------------------


def update_folder(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
    name: str | None = None,
    parent_id: str | None = None,
    parent_folder_path: str | None = None,
) -> FolderInfo:
    """
    Update a folder's name or parent.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        scope_id: The folder scope ID to update.
        folder_path: The folder path to update (alternative to scope_id).
        name: New name for the folder.
        parent_id: New parent scope ID.
        parent_folder_path: New parent folder path (alternative to parent_id).

    Returns:
        FolderInfo: The updated folder metadata.
    """
    try:
        logger.info("Updating folder scope_id=%s folder_path=%s", scope_id, folder_path)
        params: dict = {}
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path
        if name:
            params["name"] = name
        if parent_id:
            params["parentId"] = parent_id
        if parent_folder_path:
            params["parentFolderPath"] = parent_folder_path

        result = unique_sdk.Folder.update(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return FolderInfo.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error updating folder: %s", e)
        raise


async def update_folder_async(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
    name: str | None = None,
    parent_id: str | None = None,
    parent_folder_path: str | None = None,
) -> FolderInfo:
    """Async variant of :func:`update_folder`."""
    try:
        logger.info("Updating folder scope_id=%s folder_path=%s", scope_id, folder_path)
        params: dict = {}
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path
        if name:
            params["name"] = name
        if parent_id:
            params["parentId"] = parent_id
        if parent_folder_path:
            params["parentFolderPath"] = parent_folder_path

        result = await unique_sdk.Folder.update_async(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return FolderInfo.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error updating folder: %s", e)
        raise


# ---------------------------------------------------------------------------
# Delete folder
# ---------------------------------------------------------------------------


def delete_folder(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
    recursive: bool = False,
) -> DeleteFolderResponse:
    """
    Delete a folder by ID or path.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        scope_id: The folder scope ID.
        folder_path: The folder path (alternative to scope_id).
        recursive: Whether to delete child folders recursively.

    Returns:
        DeleteFolderResponse: The delete result with success/failure details.
    """
    try:
        logger.info(
            "Deleting folder scope_id=%s folder_path=%s recursive=%s",
            scope_id,
            folder_path,
            recursive,
        )
        params: dict = {"recursive": recursive}
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path

        result = unique_sdk.Folder.delete(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return DeleteFolderResponse.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error deleting folder: %s", e)
        raise


async def delete_folder_async(
    user_id: str,
    company_id: str,
    *,
    scope_id: str | None = None,
    folder_path: str | None = None,
    recursive: bool = False,
) -> DeleteFolderResponse:
    """Async variant of :func:`delete_folder`."""
    try:
        logger.info(
            "Deleting folder scope_id=%s folder_path=%s recursive=%s",
            scope_id,
            folder_path,
            recursive,
        )
        params: dict = {"recursive": recursive}
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path

        result = await unique_sdk.Folder.delete_async(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return DeleteFolderResponse.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error deleting folder: %s", e)
        raise


# ---------------------------------------------------------------------------
# Ingestion config
# ---------------------------------------------------------------------------


def update_ingestion_config(
    user_id: str,
    company_id: str,
    *,
    ingestion_config: dict,
    apply_to_sub_scopes: bool = False,
    scope_id: str | None = None,
    folder_path: str | None = None,
) -> Folder:
    """
    Update the ingestion configuration of a folder.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        ingestion_config: The new ingestion configuration dict.
        apply_to_sub_scopes: Whether to propagate the config to child folders.
        scope_id: The folder scope ID.
        folder_path: The folder path (alternative to scope_id).

    Returns:
        Folder: The updated folder.
    """
    try:
        logger.info(
            "Updating ingestion config scope_id=%s folder_path=%s",
            scope_id,
            folder_path,
        )
        params: dict = {
            "ingestionConfig": ingestion_config,
            "applyToSubScopes": apply_to_sub_scopes,
        }
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path

        result = unique_sdk.Folder.update_ingestion_config(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return Folder.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error updating ingestion config: %s", e)
        raise


async def update_ingestion_config_async(
    user_id: str,
    company_id: str,
    *,
    ingestion_config: dict,
    apply_to_sub_scopes: bool = False,
    scope_id: str | None = None,
    folder_path: str | None = None,
) -> Folder:
    """Async variant of :func:`update_ingestion_config`."""
    try:
        logger.info(
            "Updating ingestion config scope_id=%s folder_path=%s",
            scope_id,
            folder_path,
        )
        params: dict = {
            "ingestionConfig": ingestion_config,
            "applyToSubScopes": apply_to_sub_scopes,
        }
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path

        result = await unique_sdk.Folder.update_ingestion_config_async(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return Folder.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error updating ingestion config: %s", e)
        raise


# ---------------------------------------------------------------------------
# Access management
# ---------------------------------------------------------------------------


def _build_scope_accesses(
    accesses: list[FolderScopeAccess],
) -> list[dict]:
    return [
        {
            "entityId": a.entity_id,
            "type": a.type.value,
            "entityType": a.entity_type.value,
        }
        for a in accesses
    ]


def add_folder_access(
    user_id: str,
    company_id: str,
    *,
    scope_accesses: list[FolderScopeAccess],
    apply_to_sub_scopes: bool = False,
    scope_id: str | None = None,
    folder_path: str | None = None,
) -> Folder:
    """
    Add access entries to a folder.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        scope_accesses: Access entries to add.
        apply_to_sub_scopes: Whether to propagate to child folders.
        scope_id: The folder scope ID.
        folder_path: The folder path (alternative to scope_id).

    Returns:
        Folder: The updated folder.
    """
    try:
        logger.info(
            "Adding folder access scope_id=%s folder_path=%s", scope_id, folder_path
        )
        params: dict = {
            "scopeAccesses": _build_scope_accesses(scope_accesses),
            "applyToSubScopes": apply_to_sub_scopes,
        }
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path

        result = unique_sdk.Folder.add_access(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return Folder.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error adding folder access: %s", e)
        raise


async def add_folder_access_async(
    user_id: str,
    company_id: str,
    *,
    scope_accesses: list[FolderScopeAccess],
    apply_to_sub_scopes: bool = False,
    scope_id: str | None = None,
    folder_path: str | None = None,
) -> Folder:
    """Async variant of :func:`add_folder_access`."""
    try:
        logger.info(
            "Adding folder access scope_id=%s folder_path=%s", scope_id, folder_path
        )
        params: dict = {
            "scopeAccesses": _build_scope_accesses(scope_accesses),
            "applyToSubScopes": apply_to_sub_scopes,
        }
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path

        result = await unique_sdk.Folder.add_access_async(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return Folder.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error adding folder access: %s", e)
        raise


def remove_folder_access(
    user_id: str,
    company_id: str,
    *,
    scope_accesses: list[FolderScopeAccess],
    apply_to_sub_scopes: bool = False,
    scope_id: str | None = None,
    folder_path: str | None = None,
) -> Folder:
    """
    Remove access entries from a folder.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        scope_accesses: Access entries to remove.
        apply_to_sub_scopes: Whether to propagate to child folders.
        scope_id: The folder scope ID.
        folder_path: The folder path (alternative to scope_id).

    Returns:
        Folder: The updated folder.
    """
    try:
        logger.info(
            "Removing folder access scope_id=%s folder_path=%s", scope_id, folder_path
        )
        params: dict = {
            "scopeAccesses": _build_scope_accesses(scope_accesses),
            "applyToSubScopes": apply_to_sub_scopes,
        }
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path

        result = unique_sdk.Folder.remove_access(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return Folder.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error removing folder access: %s", e)
        raise


async def remove_folder_access_async(
    user_id: str,
    company_id: str,
    *,
    scope_accesses: list[FolderScopeAccess],
    apply_to_sub_scopes: bool = False,
    scope_id: str | None = None,
    folder_path: str | None = None,
) -> Folder:
    """Async variant of :func:`remove_folder_access`."""
    try:
        logger.info(
            "Removing folder access scope_id=%s folder_path=%s", scope_id, folder_path
        )
        params: dict = {
            "scopeAccesses": _build_scope_accesses(scope_accesses),
            "applyToSubScopes": apply_to_sub_scopes,
        }
        if scope_id:
            params["scopeId"] = scope_id
        if folder_path:
            params["folderPath"] = folder_path

        result = await unique_sdk.Folder.remove_access_async(
            user_id=user_id,
            company_id=company_id,
            **params,
        )
        return Folder.model_validate(result, by_alias=True, by_name=True)
    except Exception as e:
        logger.error("Error removing folder access: %s", e)
        raise
