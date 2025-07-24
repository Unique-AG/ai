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

    # For further details about the responses parameters, see the OpenAI API documentation.
    class CreateStreamResponseParams(TypedDict):
        debugInfo: Optional[Dict[str, Any]] = None
        input: Any
        model: str
        searchContext: Optional[List["Integrated.SearchResult"]] = None
        chatId: str
        assistantMessageId: str
        userMessageId: str
        startText: str | None = None
        include: Optional[
            list[
                Literal[
                    "computer_call_output.output.image_url",
                    "file_search_call.results",
                    "message.input_image.image_url",
                    "reasoning.encrypted_content",
                ]
            ]
        ] = None
        instructions: str | None = None
        max_output_tokens: int | None = None
        metadata: Optional[Dict[str, str]] = None
        parallel_tool_calls: float | None = None
        temperature: float | None = None
        text: Any
        tool_choice: Any
        tools: Any
        top_p: float | None = None
        reasoning: Any

    class ToolCall(TypedDict):
        id: str
        name: str | None = None
        arguments: str | None = None

    class ResponsesStreamResult(TypedDict):
        id: str
        message: Message
        toolCalls: List["Integrated.ToolCall"]

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

    @classmethod
    def responses_stream(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Integrated.CreateStreamResponseParams"],
    ) -> "Integrated.ResponsesStreamResult":
        """
        Executes a call to the language model and streams to the chat in real-time.
        It automatically inserts references that are mentioned by the model.
        In the form of [sourceX]. The reference documents must be given as a list in searchContext.
        """
        return cast(
            "Integrated.Responses",
            cls._static_request(
                "post",
                "/integrated/chat/stream-responses",
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def responses_stream_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Integrated.CreateStreamResponseParams"],
    ) -> "Integrated.ResponsesStreamResult":
        """
        Executes a call to the language model and streams to the chat in real-time.
        It automatically inserts references that are mentioned by the model.
        In the form of [sourceX]. The reference documents must be given as a list in searchContext.
        """
        return cast(
            "Integrated.Responses",
            cls._static_request(
                "post",
                "/integrated/chat/stream-responses",
                user_id,
                company_id,
                params,
            ),
        )
