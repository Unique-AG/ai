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

    class Input(TypedDict):
        key: str
        title: Optional[str]
        mimeType: str
        ownerType: str
        ownerId: str
        byteSize: Optional[int]

    class UpsertParams(RequestOptions):
        input: "Content.Input"
        scopeId: str
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
        cls, user_id: str, company_id: str, **params: Unpack["Content.SearchParams"]
    ) -> List["Content"]:
        return cast(
            "Content",
            cls._static_request(
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
