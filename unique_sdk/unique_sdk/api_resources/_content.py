from enum import Enum
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    cast,
)

from typing_extensions import NotRequired, Unpack

import unique_sdk
from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Content(APIResource["Content"]):
    OBJECT_NAME: ClassVar[Literal["content.search"]] = "content.search"

    id: str
    key: str
    url: Optional[str]
    title: Optional[str]
    updatedAt: str
    chunks: Optional[List["Content.Chunk"]]
    metadata: Optional[Dict[str, Any]]
    writeUrl: Optional[str]
    readUrl: Optional[str]
    expiredAt: Optional[str]

    class QueryMode(Enum):
        Default = "default"
        Insensitive = "insensitive"

    class StringFilter(TypedDict, total=False):
        contains: Optional[str]
        endsWith: Optional[str]
        equals: Optional[str]
        gt: Optional[str]
        gte: Optional[str]
        in_: Optional[
            List[str]
        ]  # Changed 'in' to 'in_' as 'in' is a reserved keyword in Python
        lt: Optional[str]
        lte: Optional[str]
        mode: Optional["Content.QueryMode"]
        not_: Optional["Content.NestedStringFilter"]  # Changed 'not' to 'not_'
        notIn: Optional[List[str]]
        startsWith: Optional[str]

    class NestedStringFilter(StringFilter):
        not_: Optional[
            "Content.NestedStringFilter"
        ]  # Inherit from StringFilter and redefine 'not_' for nested usage

    class StringNullableFilter(TypedDict, total=False):
        contains: Optional[str]
        endsWith: Optional[str]
        equals: Optional[str]
        gt: Optional[str]
        gte: Optional[str]
        in_: Optional[List[str]]
        lt: Optional[str]
        lte: Optional[str]
        mode: Optional["Content.QueryMode"]
        not_: Optional["Content.NestedStringNullableFilter"]
        notIn: Optional[List[str]]

    class NestedStringNullableFilter(StringNullableFilter):
        not_: Optional["Content.NestedStringNullableFilter"]

    class ContentWhereInput(TypedDict, total=False):
        AND: Optional[List["Content.ContentWhereInput"]]
        NOT: Optional[List["Content.ContentWhereInput"]]
        OR: Optional[List["Content.ContentWhereInput"]]
        id: Optional["Content.StringFilter"]
        key: Optional["Content.StringFilter"]
        ownerId: Optional["Content.StringFilter"]
        title: Optional["Content.StringNullableFilter"]
        url: Optional["Content.StringNullableFilter"]

    class SearchParams(RequestOptions):
        where: "Content.ContentWhereInput"
        chatId: NotRequired[str | None]
        includeFailedContent: NotRequired[bool]

    class ContentInfoParams(TypedDict):
        """
        Parameters for the content info endpoint.
        This is used to retrieve information about content based on various filters.
        """

        metadataFilter: NotRequired[dict[str, Any] | None]
        skip: NotRequired[int | None]
        take: NotRequired[int | None]
        filePath: NotRequired[str | None]
        contentId: NotRequired[str | None]
        chatId: NotRequired[str | None]

    class ContentInfosParams(TypedDict):
        """
        Parameters for the content infos endpoint.
        This is used to retrieve information about contents based on various filters.
        """

        metadataFilter: NotRequired[dict[str, Any] | None]
        skip: NotRequired[int | None]
        take: NotRequired[int | None]
        parentId: NotRequired[str | None]

    class CustomApiOptions(TypedDict):
        apiIdentifier: str
        apiPayload: Optional[str]
        customisationType: str

    class VttConfig(TypedDict, total=False):
        languageModel: Optional[str]

    class IngestionConfig(TypedDict, total=False):
        chunkMaxTokens: Optional[int]
        chunkMaxTokensOnePager: Optional[int]
        chunkMinTokens: Optional[int]
        chunkStrategy: Optional[str]
        customApiOptions: Optional[List["Content.CustomApiOptions"]]
        documentMinTokens: Optional[int]
        excelReadMode: Optional[str]
        jpgReadMode: Optional[str]
        pdfReadMode: Optional[str]
        pptReadMode: Optional[str]
        uniqueIngestionMode: str
        vttConfig: Optional["Content.VttConfig"]
        wordReadMode: Optional[str]
        displayInChat: Optional[bool]

    class Input(TypedDict):
        key: str
        title: Optional[str]
        mimeType: str
        description: NotRequired[str | None]
        ownerType: NotRequired[str | None]
        ownerId: NotRequired[str | None]
        byteSize: NotRequired[int | None]
        ingestionConfig: NotRequired["Content.IngestionConfig | None"]
        metadata: NotRequired[dict[str, Any] | None]

    class UpsertParams(RequestOptions):
        input: "Content.Input"
        scopeId: NotRequired[str | None]
        chatId: NotRequired[str | None]
        sourceOwnerType: NotRequired[str | None]
        storeInternally: NotRequired[bool | None]
        fileUrl: NotRequired[str | None]

    class UpdateParams(RequestOptions):
        contentId: NotRequired[str]
        filePath: NotRequired[str]
        ownerId: NotRequired[str]
        parentFolderPath: NotRequired[str]
        title: NotRequired[str]
        metadata: NotRequired[dict[str, str | None]]

    class Chunk(TypedDict):
        id: str
        text: str
        startPage: Optional[int]
        endPage: Optional[int]
        order: Optional[int]

    class ContentInfo(TypedDict):
        """
        Partial representation of the content containing only the base information.
        This is used for the content info endpoint.
        """

        id: str
        key: str
        url: str | None
        title: str | None
        metadata: Dict[str, Any] | None
        mimeType: str
        description: str | None
        byteSize: int
        ownerId: str
        createdAt: str
        updatedAt: str
        expiresAt: str | None
        deletedAt: str | None
        expiredAt: str | None

    class PaginatedContentInfo(TypedDict):
        contentInfo: List["Content.ContentInfo"]
        totalCount: int

    class PaginatedContentInfos(TypedDict):
        contentInfos: List["Content.ContentInfo"]
        totalCount: int

    class DeleteParams(RequestOptions):
        contentId: NotRequired[str]
        filePath: NotRequired[str]
        chatId: NotRequired[str]

    class DeleteResponse(TypedDict):
        id: str

    class MagicTableSheetTableColumn(TypedDict):
        columnId: str
        columnName: str
        content: str

    class MagicTableRow(TypedDict):
        rowId: str
        columns: List["Content.MagicTableSheetTableColumn"]
        context: NotRequired[str]
        rowMetadata: NotRequired[str]

    class MagicTableSheetIngestionConfiguration(TypedDict):
        columnIdsInMetadata: List[str]
        columnIdsInChunkText: List[str]

    class MagicTableSheetIngestParams(TypedDict):
        data: List["Content.MagicTableRow"]
        ingestionConfiguration: "Content.MagicTableSheetIngestionConfiguration"
        metadata: Dict[str, Optional[str]]
        scopeId: str
        sheetName: str
        context: NotRequired[str]

    class MagicTableSheetRowIdToContentId(TypedDict):
        rowId: str
        contentId: str

    class MagicTableSheetResponse(TypedDict):
        rowIdsToContentIds: List["Content.MagicTableSheetRowIdToContentId"]

    @classmethod
    def search(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.SearchParams"],
    ) -> List["Content"]:
        return cast(
            List["Content"],
            cls._static_request(
                "post",
                "/content/search",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def search_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.SearchParams"],
    ) -> List["Content"]:
        return cast(
            List["Content"],
            await cls._static_request_async(
                "post",
                "/content/search",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def get_info(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.ContentInfoParams"],
    ) -> PaginatedContentInfo:
        return cast(
            Content.PaginatedContentInfo,
            cls._static_request(
                "post",
                "/content/info",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def get_info_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.ContentInfoParams"],
    ) -> PaginatedContentInfo:
        return cast(
            Content.PaginatedContentInfo,
            await cls._static_request_async(
                "post",
                "/content/info",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def get_infos(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.ContentInfosParams"],
    ) -> "Content.PaginatedContentInfos":
        return cast(
            Content.PaginatedContentInfos,
            cls._static_request(
                "post",
                "/content/infos",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def get_infos_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.ContentInfosParams"],
    ) -> "Content.PaginatedContentInfos":
        return cast(
            Content.PaginatedContentInfos,
            await cls._static_request_async(
                "post",
                "/content/infos",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def upsert(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.UpsertParams"],
    ) -> "Content":
        """
        UpsertsContent
        """
        if "input" in params:
            params["input"]["metadata"] = params["input"].get("metadata") or {}
            if "description" in params["input"] and not params["input"]["description"]:
                params["input"].pop("description")

        return cast(
            "Content",
            cls._static_request(
                "post",
                "/content/upsert",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def upsert_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.UpsertParams"],
    ) -> "Content":
        """
        UpsertsContent
        """
        if "input" in params:
            params["input"]["metadata"] = params["input"].get("metadata") or {}
            if "description" in params["input"] and not params["input"]["description"]:
                params["input"].pop("description")

        return cast(
            "Content",
            await cls._static_request_async(
                "post",
                "/content/upsert",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def ingest_magic_table_sheets(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.MagicTableSheetIngestParams"],
    ) -> "Content.MagicTableSheetResponse":
        return cast(
            Content.MagicTableSheetResponse,
            cls._static_request(
                "post",
                "/content/magic-table-sheets",
                user_id,
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    async def ingest_magic_table_sheets_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.MagicTableSheetIngestParams"],
    ) -> "Content.MagicTableSheetResponse":
        return cast(
            Content.MagicTableSheetResponse,
            await cls._static_request_async(
                "post",
                "/content/magic-table-sheets",
                user_id,
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    def update(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.UpdateParams"],
    ) -> "Content.ContentInfo":
        content_id = cls.resolve_content_id_from_file_path(
            user_id=user_id,
            company_id=company_id,
            content_id=params.get("contentId"),
            file_path=params.get("filePath"),
        )
        owner_id = unique_sdk.Folder.resolve_scope_id_from_folder_path(
            user_id,
            company_id,
            params.get("ownerId"),
            params.get("parentFolderPath"),
        )
        params.pop("contentId", None)
        params.pop("filePath", None)
        params.pop("parentFolderPath", None)
        if owner_id is not None:
            params["ownerId"] = owner_id

        return cast(
            "Content.ContentInfo",
            cls._static_request(
                "patch",
                f"/content/{content_id}",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def update_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.UpdateParams"],
    ) -> "Content.ContentInfo":
        content_id = cls.resolve_content_id_from_file_path(
            user_id,
            company_id,
            params.get("contentId"),
            params.get("filePath"),
        )
        owner_id = unique_sdk.Folder.resolve_scope_id_from_folder_path(
            user_id,
            company_id,
            params.get("ownerId"),
            params.get("parentFolderPath"),
        )
        params.pop("contentId", None)
        params.pop("filePath", None)
        params.pop("parentFolderPath", None)
        if owner_id is not None:
            params["ownerId"] = owner_id

        return cast(
            "Content.ContentInfo",
            await cls._static_request_async(
                "patch",
                f"/content/{content_id}",
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
        **params: Unpack["Content.DeleteParams"],
    ) -> "Content.DeleteResponse":
        """
        Deletes a content by its id or file path.
        """
        content_id = cls.resolve_content_id_from_file_path(
            user_id,
            company_id,
            params.get("contentId"),
            params.get("filePath"),
        )
        params.pop("contentId", None)
        params.pop("filePath", None)

        return cast(
            "Content.DeleteResponse",
            cls._static_request(
                "delete",
                f"/content/{content_id}",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def delete_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.DeleteParams"],
    ) -> "Content.DeleteResponse":
        """
        Async deletes a content by its id or file path.
        """
        content_id = cls.resolve_content_id_from_file_path(
            user_id,
            company_id,
            params.get("contentId"),
            params.get("filePath"),
        )
        params.pop("contentId", None)
        params.pop("filePath", None)

        return cast(
            "Content.DeleteResponse",
            await cls._static_request_async(
                "delete",
                f"/content/{content_id}",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def resolve_content_id_from_file_path(
        cls,
        user_id: str,
        company_id: str,
        content_id: str | None = None,
        file_path: str | None = None,
    ) -> str | None:
        """
        Returns the contentId to use: if content_id is provided, returns it;
        if not, but file_path is provided, resolves and returns the id for that file path.

        Returns:
            str: The resolved content ID.
            None: Failed to resolve a content ID (e.g., file_path not found or not provided).
        """
        if content_id:
            return content_id
        if file_path:
            file_info = cls.get_info(
                user_id=user_id,
                company_id=company_id,
                filePath=file_path,
            )
            content_infos = file_info.get("contentInfo")
            resolved_id = (
                content_infos[0].get("id")
                if file_info.get("totalCount", 0) > 0
                and content_infos is not None
                and len(content_infos) > 0
                else None
            )
            if not resolved_id:
                raise ValueError(f"Could not find file with filePath: {file_path}")
            return resolved_id
        return None
