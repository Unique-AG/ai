from typing import (
    ClassVar,
    List,
    Literal,
    NotRequired,
    Optional,
    TypedDict,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class ChatCompletionRequestMessage(TypedDict, total=False):
    role: Literal["system", "user", "assistant"]
    content: str
    name: Optional[str]
    tool_call_id: Optional[str]


class ChatCompletionResponseMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionChoicesInner(TypedDict):
    index: int
    message: ChatCompletionResponseMessage
    finish_reason: str


class ChatCompletion(APIResource["ChatCompletion"]):
    OBJECT_NAME: ClassVar[Literal["openai.chat.completion"]] = "openai.chat.completion"

    class CreateParams(RequestOptions):
        model: NotRequired[
            Literal[
                "AZURE_GPT_4_0613",
                "AZURE_GPT_4_32K_0613",
            ]
        ]
        timeout: NotRequired[Optional["int"]]
        messages: List[ChatCompletionRequestMessage]

    model: Literal[
        "AZURE_GPT_4_0613",
        "AZURE_GPT_4_32K_0613",
    ]
    choices: List[ChatCompletionChoicesInner]

    @classmethod
    def create(
        cls, company_id: str, **params: Unpack["ChatCompletion.CreateParams"]
    ) -> "ChatCompletion":
        return cast(
            "ChatCompletion",
            cls._static_request(
                "post",
                cls.class_url(),
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls, company_id: str, **params: Unpack["ChatCompletion.CreateParams"]
    ) -> "ChatCompletion":
        return cast(
            "ChatCompletion",
            await cls._static_request_async(
                "post",
                cls.class_url(),
                company_id=company_id,
                params=params,
            ),
        )
