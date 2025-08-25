from enum import Enum
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

        class ScopeAccessType(Enum):
            """
            Enum for scope access levels.
            """

            READ = "READ"
            WRITE = "WRITE"

        class ScopeAccessEntityType(Enum):
            """
            Enum for scope access entity types.
            """

            USER = "USER"
            GROUP = "GROUP"

        entityId: str
        type: ScopeAccessType
        entityType: ScopeAccessEntityType
        createdAt: str | None = None

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
        chunkMaxTokens: int | None
        chunkMaxTokensOnePager: int | None
        chunkMinTokens: int | None
        chunkStrategy: str | None
        customApiOptions: List["Folder.CustomApiOptions"] | None
        documentMinTokens: int | None
        excelReadMode: str | None
        jpgReadMode: str | None
        pdfReadMode: str | None
        pptReadMode: str | None
        uniqueIngestionMode: str
        vttConfig: Optional["Folder.VttConfig"]
        wordReadMode: str | None

    class CreatedFolder(TypedDict):
        id: str
        object: str
        name: str
        parentId: Optional[str]

    class CreateFolderStructureResponse(TypedDict):
        createdFolders: List["Folder.CreatedFolder"]

    class CreateParams(RequestOptions):
        paths: List[str]

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

    id: str
    name: str
    scopeAccess: List[ScopeAccess]
    children: List[Children]

    class UpdateIngestionConfigParams(TypedDict):
        """
        Parameters for updating folder ingestion config.
        """

        scopeId: str | None
        folderPath: str | None
        ingestionConfig: "Folder.IngestionConfig"
        applyToSubScopes: bool

    class AddAccessParams(TypedDict):
        """
        Parameters for adding access to a folder.
        """

        scopeId: str | None
        folderPath: str | None
        scopeAccesses: List["Folder.ScopeAccess"]
        applyToSubScopes: bool

    class RemoveAccessParams(TypedDict):
        """
        Parameters for removing access from a folder.
        """

        scopeId: str | None
        folderPath: str | None
        scopeAccesses: List["Folder.ScopeAccess"]
        applyToSubScopes: bool

    class DeleteFolderParams(TypedDict):
        """
        Parameters for deleting a folder.
        """

        scopeId: NotRequired[str]
        folderPath: NotRequired[str]

    class GetParams(RequestOptions):
        """
        Parameters for getting a folder by its Id or path.
        """

        scopeId: str | None = None
        folderPath: str | None = None

    class GetInfosParams(RequestOptions):
        """
        Parameters for getting multiple paginated folders by their parent Id.
        """

        parentId: NotRequired[str]
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
    ) -> "List[Folder.FolderInfo]":
        """
        Get paginated folders based on parentId. If the parentId is not defined, the root folders will be returned.
        """
        return cast(
            "List[Folder.FolderInfo]",
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
    ) -> "List[Folder.FolderInfo]":
        """
        Async get paginated folders based on parentId. If the parentId is not defined, the root folders will be returned.
        """
        return cast(
            "List[Folder.FolderInfo]",
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
            "Folder",
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
            "Folder",
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
    def delete(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.DeleteFolderParams"],
    ) -> "Folder.DeleteResponse":
        """
        Delete a folder by its ID or path.
        """

        cls._resolve_scope_id_from_folder_path(user_id, company_id, params)
        return cast(
            "Folder.DeleteResponse",
            cls._static_request(
                "delete",
                f"{cls.RESOURCE_URL}/{params.get('scopeId')}",
                user_id,
                company_id=company_id,
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
        cls._resolve_scope_id_from_folder_path(user_id, company_id, params)
        return cast(
            "Folder.DeleteResponse",
            await cls._static_request_async(
                "delete",
                f"{cls.RESOURCE_URL}/{params.get('scopeId')}",
                user_id,
                company_id=company_id,
            ),
        )

    @classmethod
    def _resolve_scope_id_from_folder_path(
        cls,
        user_id: str,
        company_id: str,
        params: dict,
    ) -> None:
        """
        If scopeId is not provided but folderPath is, resolve the folderPath to scopeId.
        Modifies params in-place.
        """
        scope_id = params.get("scopeId")
        folder_path = params.get("folderPath")
        if not scope_id:
            folder_info = cls.get_info(
                user_id=user_id,
                company_id=company_id,
                folderPath=folder_path,
            )
            resolved_id = folder_info.get("id")
            if not resolved_id:
                raise ValueError(
                    f"Could not resolve folder id from folderPath: {folder_path}"
                )
            params["scopeId"] = resolved_id
            params.pop("folderPath", None)
