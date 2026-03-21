from typing import Any

from unique_sdk.api_resources._folder import Folder

from .._base import BaseManager, DomainObject


class FolderObject(DomainObject):
    """A knowledge-base folder with mutation methods."""

    async def update(self, **params: Any) -> "FolderObject":
        result = await Folder.update_async(self._user_id, self._company_id, **params)
        self._update_raw(result)
        return self

    async def update_ingestion_config(self, **params: Any) -> "FolderObject":
        result = await Folder.update_ingestion_config_async(
            self._user_id, self._company_id, **params
        )
        self._update_raw(result)
        return self

    async def add_access(self, **params: Any) -> "FolderObject":
        result = await Folder.add_access_async(
            self._user_id, self._company_id, **params
        )
        self._update_raw(result)
        return self

    async def remove_access(self, **params: Any) -> Any:
        return await Folder.remove_access_async(
            self._user_id, self._company_id, **params
        )

    async def delete(self, **params: Any) -> Any:
        return await Folder.delete_async(self._user_id, self._company_id, **params)


class FolderManager(BaseManager):
    """Create and manage knowledge-base folders."""

    async def get_path(self, scope_id: str) -> Any:
        return await Folder.get_folder_path_async(
            self._user_id, self._company_id, scope_id
        )

    async def get_info(self, **params: Any) -> Any:
        return await Folder.get_info_async(self._user_id, self._company_id, **params)

    async def get_infos(self, **params: Any) -> Any:
        return await Folder.get_infos_async(self._user_id, self._company_id, **params)

    async def create_paths(self, **params: Any) -> Any:
        return await Folder.create_paths_async(
            self._user_id, self._company_id, **params
        )

    async def update(self, **params: Any) -> Any:
        return await Folder.update_async(self._user_id, self._company_id, **params)

    async def delete(self, **params: Any) -> Any:
        return await Folder.delete_async(self._user_id, self._company_id, **params)

    async def resolve_scope_id(
        self,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> str | None:
        return await Folder.resolve_scope_id_from_folder_path_async(
            self._user_id,
            self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
        )

    async def resolve_scope_id_with_create(
        self,
        scope_id: str | None = None,
        folder_path: str | None = None,
        create_if_not_exists: bool = True,
    ) -> str | None:
        return await Folder.resolve_scope_id_from_folder_path_with_create_async(
            self._user_id,
            self._company_id,
            scope_id=scope_id,
            folder_path=folder_path,
            create_if_not_exists=create_if_not_exists,
        )
