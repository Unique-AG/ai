from typing import List, Literal, TypedDict, cast

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class HistoryMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    text: str


class SearchString(APIResource["SearchString"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["search.search-string"]:
        return "search.search-string"

    class CreateParams(RequestOptions):
        prompt: str
        chatId: NotRequired["str"]
        messages: NotRequired[List[HistoryMessage]]
        languageModel: NotRequired[
            Literal[
                "AZURE_GPT_4_0613",
                "AZURE_GPT_4_32K_0613",
                "AZURE_GPT_4_TURBO_1106",
            ]
        ]

    @classmethod
    def create(
        cls, user_id, company_id, **params: Unpack["SearchString.CreateParams"]
    ) -> "SearchString":
        return cast(
            "SearchString",
            cls._static_request(
                "post",
                "/search/search-string",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls, user_id, company_id, **params: Unpack["SearchString.CreateParams"]
    ) -> "SearchString":
        return cast(
            "SearchString",
            await cls._static_request_async(
                "post",
                "/search/search-string",
                user_id,
                company_id,
                params=params,
            ),
        )
