from enum import Enum
from typing import (
    Any,
    Literal,
    TypedDict,
    cast,
)

from typing_extensions import NotRequired, Unpack

import unique_sdk
from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class Content(APIResource["Content"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["content.search"]:
        return "content.search"

    id: str
    key: str
    url: str | None
    title: str | None
    updatedAt: str
    chunks: list["Content.Chunk"] | None
    metadata: dict[str, Any] | None
    writeUrl: str | None
    readUrl: str | None
    expiredAt: str | None
    appliedIngestionConfig: dict[str, Any] | None

    class QueryMode(Enum):
        Default = "default"
        Insensitive = "insensitive"

    class StringFilter(TypedDict, total=False):
        contains: str | None
        endsWith: str | None
        equals: str | None
        gt: str | None
        gte: str | None
        in_: (
            list[str] | None
        )  # Changed 'in' to 'in_' as 'in' is a reserved keyword in Python
        lt: str | None
        lte: str | None
        mode: "Content.QueryMode | None"  # quoted: basedpyright can't use | with unresolved forward ref
        not_: "Content.NestedStringFilter | None"  # Changed 'not' to 'not_'
        notIn: list[str] | None
        startsWith: str | None

    class NestedStringFilter(StringFilter):
        pass  # not_ inherited from StringFilter as Optional[NestedStringFilter]

    class StringNullableFilter(TypedDict, total=False):
        contains: str | None
        endsWith: str | None
        equals: str | None
        gt: str | None
        gte: str | None
        in_: list[str] | None
        lt: str | None
        lte: str | None
        mode: "Content.QueryMode | None"
        not_: "Content.NestedStringNullableFilter | None"
        notIn: list[str] | None

    class NestedStringNullableFilter(StringNullableFilter):
        pass  # not_ inherited from StringNullableFilter

    class ContentWhereInput(TypedDict, total=False):
        AND: list["Content.ContentWhereInput"] | None
        NOT: list["Content.ContentWhereInput"] | None
        OR: list["Content.ContentWhereInput"] | None
        id: "Content.StringFilter | None"
        key: "Content.StringFilter | None"
        ownerId: "Content.StringFilter | None"
        title: "Content.StringNullableFilter | None"
        url: "Content.StringNullableFilter | None"

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
        parentFolderPath: NotRequired[str | None]

    class CustomApiOptions(TypedDict):
        apiIdentifier: str
        apiPayload: str | None
        customisationType: str

    class VttConfig(TypedDict, total=False):
        languageModel: str | None

    class IngestionConfig(TypedDict, total=False):
        chunkMaxTokens: int | None
        chunkMaxTokensOnePager: int | None
        chunkMinTokens: int | None
        chunkStrategy: str | None
        customApiOptions: list["Content.CustomApiOptions"] | None
        documentMinTokens: int | None
        excelReadMode: str | None
        jpgReadMode: str | None
        pdfReadMode: str | None
        pptReadMode: str | None
        uniqueIngestionMode: str
        vttConfig: "Content.VttConfig | None"
        wordReadMode: str | None
        hideInChat: bool | None

    class Input(TypedDict):
        key: str
        title: str | None
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
        parentFolderPath: NotRequired[str | None]
        createFolderIfNotExists: NotRequired[bool | None]
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

    class UpdateIngestionStateParams(RequestOptions):
        contentId: str
        ingestionState: str

    class Chunk(TypedDict):
        id: str
        text: str
        startPage: int | None
        endPage: int | None
        order: int | None

    class ContentInfo(TypedDict):
        """
        Partial representation of the content containing only the base information.
        This is used for the content info endpoint.
        """

        id: str
        key: str
        url: str | None
        title: str | None
        metadata: dict[str, Any] | None
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
        contentInfo: list["Content.ContentInfo"]
        totalCount: int

    class PaginatedContentInfos(TypedDict):
        contentInfos: list["Content.ContentInfo"]
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
        columns: list["Content.MagicTableSheetTableColumn"]
        context: NotRequired[str]
        rowMetadata: NotRequired[str]

    class MagicTableSheetIngestionConfiguration(TypedDict):
        columnIdsInMetadata: list[str]
        columnIdsInChunkText: list[str]

    class MagicTableSheetIngestParams(TypedDict):
        data: list["Content.MagicTableRow"]
        ingestionConfiguration: "Content.MagicTableSheetIngestionConfiguration"
        metadata: dict[str, str | None]
        scopeId: str
        sheetName: str
        context: NotRequired[str]

    class MagicTableSheetRowIdToContentId(TypedDict):
        rowId: str
        contentId: str

    class MagicTableSheetResponse(TypedDict):
        rowIdsToContentIds: list["Content.MagicTableSheetRowIdToContentId"]

    @classmethod
    def search(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.SearchParams"],
    ) -> list["Content"]:
        return cast(
            list["Content"],
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
    ) -> list["Content"]:
        return cast(
            list["Content"],
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
        parent_id = unique_sdk.Folder.resolve_scope_id_from_folder_path(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("parentId"),
            folder_path=params.get("parentFolderPath"),
        )
        params.pop("parentFolderPath", None)
        if parent_id:
            params["parentId"] = parent_id

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
        parent_id = await unique_sdk.Folder.resolve_scope_id_from_folder_path_async(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("parentId"),
            folder_path=params.get("parentFolderPath"),
        )
        params.pop("parentFolderPath", None)
        if parent_id:
            params["parentId"] = parent_id

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

        create_folder = params.get("createFolderIfNotExists")
        scope_id = unique_sdk.Folder.resolve_scope_id_from_folder_path_with_create(
            user_id=user_id,
            company_id=company_id,
            scope_id=params.get("scopeId"),
            folder_path=params.get("parentFolderPath"),
            create_if_not_exists=create_folder if create_folder is not None else True,
        )
        params.pop("parentFolderPath", None)
        params.pop("createFolderIfNotExists", None)
        if scope_id:
            params["scopeId"] = scope_id

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

        create_folder = params.get("createFolderIfNotExists")
        scope_id = (
            await unique_sdk.Folder.resolve_scope_id_from_folder_path_with_create_async(
                user_id=user_id,
                company_id=company_id,
                scope_id=params.get("scopeId"),
                folder_path=params.get("parentFolderPath"),
                create_if_not_exists=create_folder
                if create_folder is not None
                else True,
            )
        )
        params.pop("parentFolderPath", None)
        params.pop("createFolderIfNotExists", None)
        if scope_id:
            params["scopeId"] = scope_id

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
    def update(  # pyright: ignore[reportIncompatibleMethodOverride]
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
        owner_id = await unique_sdk.Folder.resolve_scope_id_from_folder_path_async(
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
    def update_ingestion_state(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.UpdateIngestionStateParams"],
    ) -> "Content.ContentInfo":
        content_id = params.get("contentId")
        ingestion_state = params.get("ingestionState")

        return cast(
            "Content.ContentInfo",
            cls._static_request(
                "patch",
                f"/content/{content_id}/ingestion-state",
                user_id,
                company_id,
                params={"ingestionState": ingestion_state},
            ),
        )

    @classmethod
    async def update_ingestion_state_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.UpdateIngestionStateParams"],
    ) -> "Content.ContentInfo":
        content_id = params.get("contentId")
        ingestion_state = params.get("ingestionState")

        return cast(
            "Content.ContentInfo",
            await cls._static_request_async(
                "patch",
                f"/content/{content_id}/ingestion-state",
                user_id,
                company_id,
                params={"ingestionState": ingestion_state},
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
            # contentInfo is typed non-optional in the TypedDict, but .get() returns None
            # when the key is absent at runtime (API schema drift or untyped caller).
            resolved_id = (
                content_infos[0].get("id")
                if file_info.get("totalCount", 0) > 0
                and content_infos is not None  # pyright: ignore[reportUnnecessaryComparison]
                and len(content_infos) > 0
                else None
            )
            if not resolved_id:
                raise ValueError(f"Could not find file with filePath: {file_path}")
            return resolved_id
        return None
