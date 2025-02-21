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

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk.api_resources._message import Message


class Integrated(APIResource["Integrated"]):
    """
    This object represents the integrated route. It is used to run complex APIs on the Unique platform
    """

    OBJECT_NAME: ClassVar[Literal["integrated"]] = "integrated"

    class SearchResult(TypedDict, total=False):
        id: str
        chunkId: str
        key: str
        title: NotRequired["str"]
        url: NotRequired["str"]

    class ChatCompletionRequestMessage(TypedDict, total=False):
        role: Literal["system", "user", "assistant"]
        content: str
        name: Optional[str]

    class CreateStream(RequestOptions):
        model: NotRequired[
            Literal[
                "AZURE_GPT_4_0613",
                "AZURE_GPT_4_32K_0613",
            ]
        ]
        timeout: NotRequired["int"]
        messages: List["Integrated.ChatCompletionRequestMessage"]
        searchContext: NotRequired[List["Integrated.SearchResult"]]
        chatId: str
        assistantId: str
        assistantMessageId: str
        userMessageId: str
        startText: NotRequired["str"]
        debugInfo: NotRequired[Dict[str, Any]]

    @classmethod
    def chat_stream_completion(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Integrated.CreateStream"],
    ) -> "Message":
        """
        Executes a call to the language model and streams to the chat in real-time.
        It automatically inserts references that are mentioned by the model.
        In the form of [sourceX]. The reference documents must be given as a list in searchContext.
        """
        url = "/integrated/chat/stream-completions"
        return cast(
            "Message",
            cls._static_request(
                "post",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def chat_stream_completion_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Integrated.CreateStream"],
    ) -> "Message":
        """
        Executes a call to the language model and streams to the chat in real-time.
        It automatically inserts references that are mentioned by the model.
        In the form of [sourceX]. The reference documents must be given as a list in searchContext.
        """
        url = "/integrated/chat/stream-completions"
        return cast(
            "Message",
            await cls._static_request_async(
                "post",
                url,
                user_id,
                company_id,
                params,
            ),
        )
