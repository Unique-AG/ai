from enum import Enum
from typing import Any, ClassVar, Dict, List, Literal, Optional, TypedDict, cast

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Content(APIResource["Content"]):
    OBJECT_NAME: ClassVar[Literal["content.search"]] = "content.search"

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
        chatId: NotRequired[str]

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

    class Input(TypedDict):
        key: str
        title: Optional[str]
        mimeType: str
        ownerType: str
        ownerId: str
        byteSize: Optional[int]
        ingestionConfig: "Content.IngestionConfig"

    class UpsertParams(RequestOptions):
        input: "Content.Input"
        scopeId: Optional[str]
        chatId: Optional[str]
        sourceOwnerType: str
        storeInternally: bool
        fileUrl: Optional[str]

    class Chunk(TypedDict):
        id: str
        text: str
        startPage: Optional[int]
        endPage: Optional[int]
        order: Optional[int]

    id: str
    key: str
    url: Optional[str]
    title: Optional[str]
    updatedAt: str
    chunks: List[Chunk]
    metadata: Optional[Dict[str, Any]]

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
    def upsert(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Content.UpsertParams"],
    ) -> "Content":
        """
        UpsertsContent
        """
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
