from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.folder_management.functions import (
    add_folder_access,
    add_folder_access_async,
    create_folders,
    create_folders_async,
    delete_folder,
    delete_folder_async,
    get_folder_info,
    get_folder_info_async,
    get_folder_path,
    get_folder_path_async,
    list_folders,
    list_folders_async,
    remove_folder_access,
    remove_folder_access_async,
    update_folder,
    update_folder_async,
    update_ingestion_config,
    update_ingestion_config_async,
)
from unique_toolkit.folder_management.schemas import (
    CreateFolderStructureResponse,
    DeleteFolderResponse,
    Folder,
    FolderInfo,
    FolderPath,
    FolderScopeAccess,
    PaginatedFolderInfos,
)


class FolderManagementService:
    """Provides methods to manage folders in the knowledge base."""

    def __init__(
        self,
        *,
        company_id: str,
        user_id: str,
    ):
        [company_id, user_id] = validate_required_values([company_id, user_id])
        self._company_id: str = company_id
        self._user_id: str = user_id

    # ------------------------------------------------------------------
    # Get folder path
    # ------------------------------------------------------------------

    def get_folder_path(self, *, scope_id: str) -> FolderPath:
        """
        Get the complete folder path for a given folder ID.

        Args:
            scope_id: The folder scope ID.

        Returns:
            FolderPath: The resolved folder path.
        """
        return get_folder_path(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
        )

    async def get_folder_path_async(self, *, scope_id: str) -> FolderPath:
        """Async variant of :meth:`get_folder_path`."""
        return await get_folder_path_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
        )

    # ------------------------------------------------------------------
    # Get folder info
    # ------------------------------------------------------------------

    def get_folder_info(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> FolderInfo:
        """
        Get info about a single folder by ID or path.

        Args:
            scope_id: The folder scope ID.
            folder_path: The folder path (alternative to scope_id).

        Returns:
            FolderInfo: The folder metadata.
        """
        return get_folder_info(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    async def get_folder_info_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> FolderInfo:
        """Async variant of :meth:`get_folder_info`."""
        return await get_folder_info_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    # ------------------------------------------------------------------
    # List folders
    # ------------------------------------------------------------------

    def list_folders(
        self,
        *,
        parent_id: str | None = None,
        parent_folder_path: str | None = None,
        take: int | None = None,
        skip: int | None = None,
    ) -> PaginatedFolderInfos:
        """
        List folders under a parent, with pagination. Returns root folders
        when no parent is specified.

        Args:
            parent_id: Scope ID of the parent folder.
            parent_folder_path: Path of the parent folder.
            take: Maximum number of folders to return.
            skip: Number of folders to skip.

        Returns:
            PaginatedFolderInfos: Paginated list of folder info objects.
        """
        return list_folders(
            user_id=self._user_id,
            company_id=self._company_id,
            parent_id=parent_id,
            parent_folder_path=parent_folder_path,
            take=take,
            skip=skip,
        )

    async def list_folders_async(
        self,
        *,
        parent_id: str | None = None,
        parent_folder_path: str | None = None,
        take: int | None = None,
        skip: int | None = None,
    ) -> PaginatedFolderInfos:
        """Async variant of :meth:`list_folders`."""
        return await list_folders_async(
            user_id=self._user_id,
            company_id=self._company_id,
            parent_id=parent_id,
            parent_folder_path=parent_folder_path,
            take=take,
            skip=skip,
        )

    # ------------------------------------------------------------------
    # Create folders
    # ------------------------------------------------------------------

    def create_folders(
        self,
        *,
        paths: list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_paths: list[str] | None = None,
        inherit_access: bool = True,
    ) -> CreateFolderStructureResponse:
        """
        Create one or more folders by path.

        Args:
            paths: Absolute folder paths to create.
            parent_scope_id: Parent scope ID when using relative paths.
            relative_paths: Relative paths to create under parent_scope_id.
            inherit_access: Whether created folders inherit parent access.

        Returns:
            CreateFolderStructureResponse: The created folders.
        """
        return create_folders(
            user_id=self._user_id,
            company_id=self._company_id,
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_paths=relative_paths,
            inherit_access=inherit_access,
        )

    async def create_folders_async(
        self,
        *,
        paths: list[str] | None = None,
        parent_scope_id: str | None = None,
        relative_paths: list[str] | None = None,
        inherit_access: bool = True,
    ) -> CreateFolderStructureResponse:
        """Async variant of :meth:`create_folders`."""
        return await create_folders_async(
            user_id=self._user_id,
            company_id=self._company_id,
            paths=paths,
            parent_scope_id=parent_scope_id,
            relative_paths=relative_paths,
            inherit_access=inherit_access,
        )

    # ------------------------------------------------------------------
    # Update folder
    # ------------------------------------------------------------------

    def update_folder(
        self,
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
            scope_id: The folder scope ID to update.
            folder_path: The folder path to update.
            name: New name for the folder.
            parent_id: New parent scope ID.
            parent_folder_path: New parent folder path.

        Returns:
            FolderInfo: The updated folder metadata.
        """
        return update_folder(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            name=name,
            parent_id=parent_id,
            parent_folder_path=parent_folder_path,
        )

    async def update_folder_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        name: str | None = None,
        parent_id: str | None = None,
        parent_folder_path: str | None = None,
    ) -> FolderInfo:
        """Async variant of :meth:`update_folder`."""
        return await update_folder_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            name=name,
            parent_id=parent_id,
            parent_folder_path=parent_folder_path,
        )

    # ------------------------------------------------------------------
    # Delete folder
    # ------------------------------------------------------------------

    def delete_folder(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        recursive: bool = False,
    ) -> DeleteFolderResponse:
        """
        Delete a folder by ID or path.

        Args:
            scope_id: The folder scope ID.
            folder_path: The folder path (alternative to scope_id).
            recursive: Whether to delete child folders recursively.

        Returns:
            DeleteFolderResponse: The delete result with success/failure details.
        """
        return delete_folder(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            recursive=recursive,
        )

    async def delete_folder_async(
        self,
        *,
        scope_id: str | None = None,
        folder_path: str | None = None,
        recursive: bool = False,
    ) -> DeleteFolderResponse:
        """Async variant of :meth:`delete_folder`."""
        return await delete_folder_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            recursive=recursive,
        )

    # ------------------------------------------------------------------
    # Ingestion config
    # ------------------------------------------------------------------

    def update_ingestion_config(
        self,
        *,
        ingestion_config: dict,
        apply_to_sub_scopes: bool = False,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> Folder:
        """
        Update the ingestion configuration of a folder.

        Args:
            ingestion_config: The new ingestion configuration dict.
            apply_to_sub_scopes: Whether to propagate to child folders.
            scope_id: The folder scope ID.
            folder_path: The folder path (alternative to scope_id).

        Returns:
            Folder: The updated folder.
        """
        return update_ingestion_config(
            user_id=self._user_id,
            company_id=self._company_id,
            ingestion_config=ingestion_config,
            apply_to_sub_scopes=apply_to_sub_scopes,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    async def update_ingestion_config_async(
        self,
        *,
        ingestion_config: dict,
        apply_to_sub_scopes: bool = False,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> Folder:
        """Async variant of :meth:`update_ingestion_config`."""
        return await update_ingestion_config_async(
            user_id=self._user_id,
            company_id=self._company_id,
            ingestion_config=ingestion_config,
            apply_to_sub_scopes=apply_to_sub_scopes,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    # ------------------------------------------------------------------
    # Access management
    # ------------------------------------------------------------------

    def add_folder_access(
        self,
        *,
        scope_accesses: list[FolderScopeAccess],
        apply_to_sub_scopes: bool = False,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> Folder:
        """
        Add access entries to a folder.

        Args:
            scope_accesses: Access entries to add.
            apply_to_sub_scopes: Whether to propagate to child folders.
            scope_id: The folder scope ID.
            folder_path: The folder path (alternative to scope_id).

        Returns:
            Folder: The updated folder.
        """
        return add_folder_access(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    async def add_folder_access_async(
        self,
        *,
        scope_accesses: list[FolderScopeAccess],
        apply_to_sub_scopes: bool = False,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> Folder:
        """Async variant of :meth:`add_folder_access`."""
        return await add_folder_access_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    def remove_folder_access(
        self,
        *,
        scope_accesses: list[FolderScopeAccess],
        apply_to_sub_scopes: bool = False,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> Folder:
        """
        Remove access entries from a folder.

        Args:
            scope_accesses: Access entries to remove.
            apply_to_sub_scopes: Whether to propagate to child folders.
            scope_id: The folder scope ID.
            folder_path: The folder path (alternative to scope_id).

        Returns:
            Folder: The updated folder.
        """
        return remove_folder_access(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    async def remove_folder_access_async(
        self,
        *,
        scope_accesses: list[FolderScopeAccess],
        apply_to_sub_scopes: bool = False,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> Folder:
        """Async variant of :meth:`remove_folder_access`."""
        return await remove_folder_access_async(
            user_id=self._user_id,
            company_id=self._company_id,
            scope_accesses=scope_accesses,
            apply_to_sub_scopes=apply_to_sub_scopes,
            scope_id=scope_id,
            folder_path=folder_path,
        )
