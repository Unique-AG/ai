from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    cast,
)

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Search(APIResource["Search"]):
    OBJECT_NAME: ClassVar[Literal["search.search"]] = "search.search"

    class CreateParams(RequestOptions):
        chatId: NotRequired[Optional[str]]
        searchString: str
        searchType: Literal["VECTOR", "COMBINED"]
        language: NotRequired[Optional[str]]
        reranker: NotRequired[Optional[Dict[str, Any]]]
        scopeIds: NotRequired[Optional[List[str]]]
        chatOnly: NotRequired[Optional[bool]]
        limit: NotRequired[Optional[int]]
        page: NotRequired[Optional[int]]
        metaDataFilter: NotRequired[Optional[Dict[str, Any]]]
        contentIds: NotRequired[Optional[List[str]]]
        scoreThreshold: NotRequired[Optional[float]]

    id: str
    chunkId: str
    text: str
    createdAt: str
    updatedAt: str
    url: Optional[str]
    title: Optional[str]
    key: Optional[str]
    order: int
    startPage: int
    endPage: int
    metadata: Optional[Dict[str, Any]]

    @classmethod
    def create(
        cls, user_id: str, company_id: str, **params: Unpack["Search.CreateParams"]
    ) -> List["Search"]:
        return cast(
            List["Search"],
            cls._static_request(
                "post",
                "/search/search",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls, user_id: str, company_id: str, **params: Unpack["Search.CreateParams"]
    ) -> List["Search"]:
        return cast(
            List["Search"],
            await cls._static_request_async(
                "post",
                "/search/search",
                user_id,
                company_id,
                params=params,
            ),
        )
