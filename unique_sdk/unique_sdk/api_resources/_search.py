from typing import Any, ClassVar, Dict, List, Literal, Optional, cast

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Search(APIResource["Search"]):
    OBJECT_NAME: ClassVar[Literal["search.search"]] = "search.search"

    class CreateParams(RequestOptions):
        chatId: str
        searchString: str
        searchType: Literal["VECTOR", "COMBINED"]
        language: NotRequired[str]
        reranker: NotRequired[dict]
        scopeIds: NotRequired[List[str]]
        chatOnly: NotRequired[bool]
        limit: NotRequired[int]
        page: NotRequired[int]

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
    ) -> "Search":
        return cast(
            "Search",
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
    ) -> "Search":
        return cast(
            "Search",
            await cls._static_request_async(
                "post",
                "/search/search",
                user_id,
                company_id,
                params=params,
            ),
        )
