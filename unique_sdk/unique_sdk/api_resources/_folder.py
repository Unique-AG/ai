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

    class GetParams(RequestOptions):
        """
        Parameters for getting a folder by its Id or path.
        """

        scopeId: str | None = None
        folderPath: str | None = None

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
        take: NotRequired[int]
        skip: NotRequired[int]

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
    def update(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Folder.UpdateParams"],
    ) -> "Folder.FolderInfo":
        """
        Update a folder given its id or path. Can update the name or the parent folder by specifying its id or path.
        """

        scopeId = cls.resolve_scope_id(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("scopeId"),
            folder_path=params.get("folderPath"),
        )
        parentId = cls.resolve_scope_id(
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

        scopeId = cls.resolve_scope_id(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("scopeId"),
            folder_path=params.get("folderPath"),
        )
        parentId = cls.resolve_scope_id(
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
    def resolve_scope_id(
        cls,
        user_id: str,
        company_id: str,
        scope_id: str | None = None,
        folder_path: str | None = None,
    ) -> str | None:
        """
        Returns the scopeId to use: if scope_id is provided, returns it;
        if not, but folder_path is provided, resolves and returns the id for that folder path.
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
