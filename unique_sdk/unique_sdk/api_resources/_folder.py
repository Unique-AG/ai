from enum import Enum
from typing import ClassVar, List, Literal, Optional, TypedDict, cast

from typing_extensions import Unpack

from unique_sdk._api_resource import APIResource


class Folder(APIResource["Folder"]):
    OBJECT_NAME: ClassVar[Literal["folder"]] = "folder"

    class ScopeAccess:
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

    id: str
    name: str
    scopeAccess: List[ScopeAccess]
    children: List[Children]

    class UpdatePropertiesParams(TypedDict):
        """
        Parameters for updating folder properties.
        """

        ingestionConfig: "Folder.IngestionConfig"
        applyToSubScopes: bool

    @classmethod
    def update_properties(
        cls,
        user_id: str,
        company_id: str,
        scope_id: str,
        **params: Unpack["Folder.UpdatePropertiesParams"],
    ) -> "Folder":
        """
        Update the properties of a folder.
        """
        return cast(
            "Folder",
            cls._static_request(
                "patch",
                f"/folder/{scope_id}/properties",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def update_properties_async(
        cls,
        user_id: str,
        company_id: str,
        scope_id: str,
        **params: Unpack["Folder.UpdatePropertiesParams"],
    ) -> "Folder":
        """
        Async update the properties of a folder.
        """
        return cast(
            "Folder",
            await cls._static_request_async(
                "patch",
                f"/folder/{scope_id}/properties",
                user_id,
                company_id,
                params=params,
            ),
        )
