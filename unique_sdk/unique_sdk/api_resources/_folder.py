from enum import Enum
from typing import ClassVar, List, Literal, Optional, TypedDict, Unpack, cast

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
            """Enum for scope access levels."""

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

    id: str
    name: str
    scopeAccess: List[ScopeAccess]
    children: List[Children]

    class UpdateIngestionConfigParams(TypedDict):
        """
        Parameters for updating folder ingestion config.
        """

        ingestionConfig: "Folder.IngestionConfig"
        applyToSubScopes: bool

    class AddAccessParams(TypedDict):
        """
        Parameters for adding access to a folder.
        """

        scopeAccesses: List["Folder.ScopeAccess"]
        applyToSubScopes: bool

    class RemoveAccessParams(TypedDict):
        """
        Parameters for removing access from a folder.
        """

        scopeAccesses: List["Folder.ScopeAccess"]
        applyToSubScopes: bool

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
        scope_id: str,
        **params: Unpack["Folder.UpdateIngestionConfigParams"],
    ) -> "Folder":
        """
        Update the ingestion config of a folder.
        """
        return cast(
            "Folder",
            cls._static_request(
                "patch",
                f"/folder/{scope_id}/ingestion-config",
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
        scope_id: str,
        **params: Unpack["Folder.UpdateIngestionConfigParams"],
    ) -> "Folder":
        """
        Async update the ingestion config of a folder.
        """
        return cast(
            "Folder",
            await cls._static_request_async(
                "patch",
                f"/folder/{scope_id}/ingestion-config",
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
        scope_id: str,
        **params: Unpack["Folder.AddAccessParams"],
    ) -> "Folder":
        """
        Add access to a folder.
        """
        return cast(
            "Folder",
            cls._static_request(
                "patch",
                f"/folder/{scope_id}/access",
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
        scope_id: str,
        **params: Unpack["Folder.AddAccessParams"],
    ) -> "Folder":
        """
        Async add access to a folder.
        """
        return cast(
            "Folder",
            await cls._static_request_async(
                "patch",
                f"/folder/{scope_id}/access",
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
        scope_id: str,
        **params: Unpack["Folder.RemoveAccessParams"],
    ) -> dict:
        """
        Remove access from a folder.
        """
        return cast(
            dict,
            cls._static_request(
                "patch",
                f"/folder/{scope_id}/remove-access",
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
        scope_id: str,
        **params: Unpack["Folder.RemoveAccessParams"],
    ) -> "Folder":
        """
        Async remove access from a folder.
        """
        return cast(
            "Folder",
            await cls._static_request_async(
                "patch",
                f"/folder/{scope_id}/remove-access",
                user_id,
                company_id,
                params=params,
            ),
        )
