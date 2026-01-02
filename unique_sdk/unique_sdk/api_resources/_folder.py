from typing import (
    ClassVar,
    List,
    Literal,
    NotRequired,
    Optional,
    TypedDict,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Folder(APIResource["Folder"]):
    OBJECT_NAME: ClassVar[Literal["folder"]] = "folder"
    RESOURCE_URL = "/folder"

    class ScopeAccess(TypedDict):
        """
        Represents the access level of a scope.
        """

        entityId: str
        type: Literal["READ", "WRITE"]
        entityType: Literal["USER", "GROUP"]
        createdAt: NotRequired[str]

    class Children(TypedDict):
        """
        Represents the children of a folder.
        """

        id: str
        name: str

    class CustomApiOptions(TypedDict):
        apiIdentifier: str
        apiPayload: str | None
        customisationType: str

    class VttConfig(TypedDict):
        languageModel: str | None

    class IngestionConfig(TypedDict):
        chunkMaxTokens: NotRequired[int | None]
        chunkMaxTokensOnePager: NotRequired[int | None]
        chunkMinTokens: NotRequired[int | None]
        chunkStrategy: NotRequired[str | None]
        customApiOptions: NotRequired[List["Folder.CustomApiOptions"] | None]
        documentMinTokens: NotRequired[int | None]
        excelReadMode: NotRequired[str | None]
        jpgReadMode: NotRequired[str | None]
        pdfReadMode: NotRequired[str | None]
        pptReadMode: NotRequired[str | None]
        uniqueIngestionMode: str
        vttConfig: NotRequired["Folder.VttConfig | None"]
        wordReadMode: NotRequired[str | None]

    class CreatedFolder(TypedDict):
        id: str
        object: str
        name: str
        parentId: Optional[str]

    class CreateFolderStructureResponse(TypedDict):
        createdFolders: List["Folder.CreatedFolder"]

    class CreateParams(RequestOptions):
        paths: List[str]
        inheritAccess: NotRequired[bool]

    class FolderInfo(TypedDict):
        """
        Represents the information of a folder.
        """

        id: str
        name: str
        ingestionConfig: "Folder.IngestionConfig"
        createdAt: str | None
        updatedAt: str | None
        parentId: str | None
        externalId: str | None

    class FolderInfos(TypedDict):
        folderInfos: List["Folder.FolderInfo"]
        totalCount: int

    id: str
    name: str
    scopeAccess: List[ScopeAccess]
    children: List[Children]

    class UpdateIngestionConfigParams(TypedDict):
        """
        Parameters for updating folder ingestion config.
        """

        scopeId: NotRequired[str | None]
        folderPath: NotRequired[str | None]
        ingestionConfig: "Folder.IngestionConfig"
        applyToSubScopes: bool

    class AddAccessParams(TypedDict):
        """
        Parameters for adding access to a folder.
        """

        scopeId: NotRequired[str | None]
        folderPath: NotRequired[str | None]
        scopeAccesses: List["Folder.ScopeAccess"]
        applyToSubScopes: bool

    class RemoveAccessParams(TypedDict):
        """
        Parameters for removing access from a folder.
        """

        scopeId: NotRequired[str | None]
        folderPath: NotRequired[str | None]
        scopeAccesses: List["Folder.ScopeAccess"]
        applyToSubScopes: bool

    class DeleteFolderParams(TypedDict):
        """
        Parameters for deleting a folder.
        """

        scopeId: NotRequired[str]
        folderPath: NotRequired[str]
        recursive: NotRequired[bool]

    class GetParams(RequestOptions):
        """
        Parameters for getting a folder by its Id or path.
        """

        scopeId: NotRequired[str]
        folderPath: NotRequired[str]

    class UpdateParams(RequestOptions):
        """
        Parameters for updating a folder.
        """

        scopeId: NotRequired[str]
        folderPath: NotRequired[str]
        parentFolderPath: NotRequired[str]
        parentId: NotRequired[str]
        name: NotRequired[str]

    class GetInfosParams(RequestOptions):
        """
        Parameters for getting multiple paginated folders by their parent Id.
        """

        parentId: NotRequired[str]
        parentFolderPath: NotRequired[str]
        take: NotRequired[int]
        skip: NotRequired[int]

    class DeleteFolderResponse(TypedDict):
        """
        Response for deleting a folder.
        """

        id: str
        name: str
        path: str
        failReason: NotRequired[str]

    class DeleteResponse(TypedDict):
        """
        Response for deleting a folder.
        """

        successFolders: List["Folder.DeleteFolderResponse"]
        failedFolders: List["Folder.DeleteFolderResponse"]

    class FolderPathResponse(TypedDict):
        """
        Response for getting folder path.
        """

        folderPath: str

    @classmethod
    def get_folder_path(
        cls,
        user_id: str,
        company_id: str,
        scope_id: str,
    ) -> "Folder.FolderPathResponse":
        """
        Get the complete folder path for a given folder ID.
        """
        return cast(
            "Folder.FolderPathResponse",
            cls._static_request(
                "get",
                f"/folder/{scope_id}/path",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def get_folder_path_async(
        cls,
        user_id: str,
        company_id: str,
        scope_id: str,
    ) -> "Folder.FolderPathResponse":
        """
        Async get the complete folder path for a given folder ID.
        """
        return cast(
            "Folder.FolderPathResponse",
            await cls._static_request_async(
                "get",
                f"/folder/{scope_id}/path",
                user_id,
                company_id,
            ),
        )

    @classmethod
    def get_info(
        cls, user_id: str, company_id: str, **params: Unpack["Folder.GetParams"]
    ) -> "Folder.FolderInfo":
        """
        Get a folder by its ID or path.
        """
        return cast(
            "Folder.FolderInfo",
            cls._static_request(
                "get",
                "/folder/info",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def get_info_async(
        cls, user_id: str, company_id: str, **params: Unpack["Folder.GetParams"]
    ) -> "Folder.FolderInfo":
        """
        Async get a folder by its ID or path.
        """
        return cast(
            "Folder.FolderInfo",
            await cls._static_request_async(
                "get",
                "/folder/info",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def get_infos(
        cls, user_id: str, company_id: str, **params: Unpack["Folder.GetInfosParams"]
    ) -> "Folder.FolderInfos":
        """
        Get paginated folders based on parentId. If the parentId is not defined, the root folders will be returned.
        """
        parent_id = cls.resolve_scope_id_from_folder_path(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("parentId"),
            folder_path=params.get("parentFolderPath"),
        )
        params.pop("parentFolderPath", None)
        if parent_id:
            params["parentId"] = parent_id

        return cast(
            "Folder.FolderInfos",
            cls._static_request(
                "get",
                "/folder/infos",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def get_infos_async(
        cls, user_id: str, company_id: str, **params: Unpack["Folder.GetInfosParams"]
    ) -> "Folder.FolderInfos":
        """
        Async get paginated folders based on parentId. If the parentId is not defined, the root folders will be returned.
        """
        parent_id = await cls.resolve_scope_id_from_folder_path_async(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("parentId"),
            folder_path=params.get("parentFolderPath"),
        )
        params.pop("parentFolderPath", None)
        if parent_id:
            params["parentId"] = parent_id

        return cast(
            "Folder.FolderInfos",
            await cls._static_request_async(
                "get",
                "/folder/infos",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def create_paths(
        cls, user_id: str, company_id: str, **params: Unpack["Folder.CreateParams"]
    ) -> "Folder.CreateFolderStructureResponse":
        return cast(
            "Folder.CreateFolderStructureResponse",
            cls._static_request(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_paths_async(
        cls, user_id: str, company_id: str, **params: Unpack["Folder.CreateParams"]
    ) -> "Folder.CreateFolderStructureResponse":
        return cast(
            "Folder.CreateFolderStructureResponse",
            await cls._static_request_async(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    def update_ingestion_config(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.UpdateIngestionConfigParams"],
    ) -> "Folder":
        """
        Update the ingestion config of a folder.
        """
        return cast(
            "Folder",
            cls._static_request(
                "patch",
                "/folder/ingestion-config",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def update_ingestion_config_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.UpdateIngestionConfigParams"],
    ) -> "Folder":
        """
        Async update the ingestion config of a folder.
        """
        return cast(
            "Folder",
            await cls._static_request_async(
                "patch",
                "/folder/ingestion-config",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def add_access(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.AddAccessParams"],
    ) -> "Folder":
        """
        Add access to a folder.
        """
        return cast(
            "Folder",
            cls._static_request(
                "patch",
                "/folder/add-access",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def add_access_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.AddAccessParams"],
    ) -> "Folder":
        """
        Async add access to a folder.
        """
        return cast(
            "Folder",
            await cls._static_request_async(
                "patch",
                "/folder/add-access",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def remove_access(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.RemoveAccessParams"],
    ) -> dict:
        """
        Remove access from a folder.
        """
        return cast(
            dict,
            cls._static_request(
                "patch",
                "/folder/remove-access",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def remove_access_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.RemoveAccessParams"],
    ) -> "Folder":
        """
        Async remove access from a folder.
        """
        return cast(
            "Folder",
            await cls._static_request_async(
                "patch",
                "/folder/remove-access",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def update(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.UpdateParams"],
    ) -> "Folder.FolderInfo":
        """
        Update a folder given its id or path. Can update the name or the parent folder by specifying its id or path.
        """

        scopeId = cls.resolve_scope_id_from_folder_path(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("scopeId"),
            folder_path=params.get("folderPath"),
        )
        parentId = cls.resolve_scope_id_from_folder_path(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("parentId"),
            folder_path=params.get("parentFolderPath"),
        )
        params.pop("folderPath", None)
        params.pop("parentFolderPath", None)
        if parentId:
            params["parentId"] = parentId

        return cast(
            "Folder.FolderInfo",
            cls._static_request(
                "patch",
                f"{cls.RESOURCE_URL}/{scopeId}",
                user_id,
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    async def update_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.UpdateParams"],
    ) -> "Folder.FolderInfo":
        """
        Async update a folder given its id or path. Can update the name or the parent folder by specifying its id or path.
        """

        scopeId = cls.resolve_scope_id_from_folder_path(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("scopeId"),
            folder_path=params.get("folderPath"),
        )
        parentId = cls.resolve_scope_id_from_folder_path(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("parentId"),
            folder_path=params.get("parentFolderPath"),
        )
        params.pop("folderPath", None)
        params.pop("parentFolderPath", None)
        if parentId:
            params["parentId"] = parentId

        return cast(
            "Folder.FolderInfo",
            await cls._static_request_async(
                "patch",
                f"{cls.RESOURCE_URL}/{scopeId}",
                user_id,
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    def delete(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.DeleteFolderParams"],
    ) -> "Folder.DeleteResponse":
        """
        Delete a folder by its ID or path.
        """

        scopeId = cls.resolve_scope_id_from_folder_path(
            user_id, company_id, params.get("scopeId"), params.get("folderPath")
        )
        params.pop("scopeId", None)
        params.pop("folderPath", None)

        return cast(
            "Folder.DeleteResponse",
            cls._static_request(
                "delete",
                f"{cls.RESOURCE_URL}/{scopeId}",
                user_id,
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    async def delete_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.DeleteFolderParams"],
    ) -> "Folder.DeleteResponse":
        """
        Async delete a folder by its ID or path.
        """
        scopeId = cls.resolve_scope_id_from_folder_path(
            user_id, company_id, params.get("scopeId"), params.get("folderPath")
        )
        params.pop("scopeId", None)
        params.pop("folderPath", None)

        return cast(
            "Folder.DeleteResponse",
            await cls._static_request_async(
                "delete",
                f"{cls.RESOURCE_URL}/{scopeId}",
                user_id,
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    def resolve_scope_id_from_folder_path(
        cls,
        user_id: str,
        company_id: str,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> str | None:
        """
        Returns the scopeId to use: if scope_id is provided, returns it;
        if not, but folder_path is provided, resolves and returns the id for that folder path.

        Returns:
            str: The resolved folder ID.
            None: Failed to resolve a folder ID (e.g., folder_path not found or not provided).
        """
        if scope_id:
            return scope_id
        if folder_path:
            folder_info = cls.get_info(
                user_id=user_id,
                company_id=company_id,
                folderPath=folder_path,
            )
            resolved_id = folder_info.get("id")
            if not resolved_id:
                raise ValueError(
                    f"Could not find a folder with folderPath: {folder_path}"
                )
            return resolved_id
        return None

    @classmethod
    def resolve_scope_id_from_folder_path_with_create(
        cls,
        user_id: str,
        company_id: str,
        scope_id: str | None = None,
        folder_path: str | None = None,
        create_if_not_exists: bool = True,
    ) -> str | None:
        if scope_id:
            return scope_id
        if folder_path:
            try:
                folder_info = cls.get_info(
                    user_id=user_id,
                    company_id=company_id,
                    folderPath=folder_path,
                )
                resolved_id = folder_info.get("id")
                if resolved_id:
                    return resolved_id
            except Exception:
                pass

            if create_if_not_exists:
                result = cls.create_paths(
                    user_id=user_id,
                    company_id=company_id,
                    paths=[folder_path],
                )
                created_folders = result.get("createdFolders", [])
                if created_folders:
                    return created_folders[-1]["id"]
                raise ValueError(
                    f"Failed to create folder with folderPath: {folder_path}"
                )

            raise ValueError(f"Could not find a folder with folderPath: {folder_path}")
        return None

    @classmethod
    async def resolve_scope_id_from_folder_path_async(
        cls,
        user_id: str,
        company_id: str,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> str | None:
        """
        Async version of resolve_scope_id_from_folder_path.
        Returns the scopeId to use: if scope_id is provided, returns it;
        if not, but folder_path is provided, resolves and returns the id for that folder path.

        Returns:
            str: The resolved folder ID.
            None: Failed to resolve a folder ID (e.g., folder_path not found or not provided).
        """
        if scope_id:
            return scope_id
        if folder_path:
            folder_info = await cls.get_info_async(
                user_id=user_id,
                company_id=company_id,
                folderPath=folder_path,
            )
            resolved_id = folder_info.get("id")
            if not resolved_id:
                raise ValueError(
                    f"Could not find a folder with folderPath: {folder_path}"
                )
            return resolved_id
        return None

    @classmethod
    async def resolve_scope_id_from_folder_path_with_create_async(
        cls,
        user_id: str,
        company_id: str,
        scope_id: str | None = None,
        folder_path: str | None = None,
        create_if_not_exists: bool = True,
    ) -> str | None:
        if scope_id:
            return scope_id
        if folder_path:
            try:
                folder_info = await cls.get_info_async(
                    user_id=user_id,
                    company_id=company_id,
                    folderPath=folder_path,
                )
                resolved_id = folder_info.get("id")
                if resolved_id:
                    return resolved_id
            except Exception:
                pass

            if create_if_not_exists:
                result = await cls.create_paths_async(
                    user_id=user_id,
                    company_id=company_id,
                    paths=[folder_path],
                )
                created_folders = result.get("createdFolders", [])
                if created_folders:
                    return created_folders[-1]["id"]
                raise ValueError(
                    f"Failed to create folder with folderPath: {folder_path}"
                )

            raise ValueError(f"Could not find a folder with folderPath: {folder_path}")
        return None
