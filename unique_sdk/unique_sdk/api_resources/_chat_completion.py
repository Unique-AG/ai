from typing import (
    Any,
    Literal,
    NotRequired,
    TypedDict,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class ChatCompletionRequestMessage(TypedDict, total=False):
    role: Literal["system", "user", "assistant"]
    content: str
    name: str | None
    tool_call_id: str | None


class ChatCompletionResponseMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionChoicesInner(TypedDict):
    index: int
    message: ChatCompletionResponseMessage
    finish_reason: str


class ChatCompletion(APIResource["ChatCompletion"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["openai.chat.completion"]:
        return "openai.chat.completion"

    class CreateParams(RequestOptions):
        model: NotRequired[
            Literal[
                "AZURE_GPT_4_0613",
                "AZURE_GPT_4_32K_0613",
            ]
        ]
        timeout: NotRequired[int | None]
        messages: list[ChatCompletionRequestMessage]
        options: NotRequired[dict[str, Any]]

    model: Literal[
        "AZURE_GPT_4_0613",
        "AZURE_GPT_4_32K_0613",
    ]
    choices: list[ChatCompletionChoicesInner]

    @classmethod
    def create(
        cls,
        company_id: str,
        user_id: str | None = None,
        **params: Unpack["ChatCompletion.CreateParams"],
    ) -> "ChatCompletion":
        return cast(
            "ChatCompletion",
            cls._static_request(
                "post",
                cls.class_url(),
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        company_id: str,
        user_id: str | None = None,
        **params: Unpack["ChatCompletion.CreateParams"],
    ) -> "ChatCompletion":
        return cast(
            "ChatCompletion",
            await cls._static_request_async(
                "post",
                cls.class_url(),
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )
