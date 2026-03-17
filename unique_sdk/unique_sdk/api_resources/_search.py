from typing import Any, Literal, NotRequired, TypedDict, Unpack, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class Search(APIResource["Search"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["search.search"]:
        return "search.search"

    class QdrantQuantizationParams(TypedDict):
        ignore: NotRequired[bool | None]
        rescore: NotRequired[bool | None]
        oversampling: NotRequired[float | None]

    class QdrantSearchParams(TypedDict):
        hnsw_ef: NotRequired[int | None]
        exact: NotRequired[bool | None]
        quantization: NotRequired["Search.QdrantQuantizationParams | None"]
        consistency: NotRequired[Literal["majority", "quorum", "all"] | int | None]

    class CreateParams(RequestOptions):
        chatId: NotRequired[str | None]
        searchString: str
        searchType: Literal["VECTOR", "COMBINED", "FULL_TEXT", "POSTGRES_FULL_TEXT"]
        language: NotRequired[str | None]
        reranker: NotRequired[dict[str, Any] | None]
        scopeIds: NotRequired[list[str] | None]
        chatOnly: NotRequired[bool | None]
        limit: NotRequired[int | None]
        page: NotRequired[int | None]
        metaDataFilter: NotRequired[dict[str, Any] | None]
        contentIds: NotRequired[list[str] | None]
        scoreThreshold: NotRequired[float | None]
        qdrantParams: NotRequired["Search.QdrantSearchParams | None"]

    id: str
    chunkId: str
    text: str
    createdAt: str
    updatedAt: str
    url: str | None
    title: str | None
    key: str | None
    order: int
    startPage: int
    endPage: int
    metadata: dict[str, Any] | None

    @classmethod
    def create(
        cls, user_id: str, company_id: str, **params: Unpack["Search.CreateParams"]
    ) -> list["Search"]:
        return cast(
            list["Search"],
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
    ) -> list["Search"]:
        return cast(
            list["Search"],
            await cls._static_request_async(
                "post",
                "/search/search",
                user_id,
                company_id,
                params=params,
            ),
        )
