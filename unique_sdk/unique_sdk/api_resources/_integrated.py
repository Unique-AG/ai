from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    List,
    Literal,
    NotRequired,
    Optional,
    Union,
    Unpack,
    cast,
)

from typing_extensions import TypedDict

# Avoid introducing a dependency on the openai sdk as it's only used for type hints
if TYPE_CHECKING:
    from openai.types.responses import (
        ResponseIncludable,
        ResponseInputParam,
        ResponseOutputItem,
        ResponseTextConfigParam,
        ToolParam,
        response_create_params,
    )
    from openai.types.shared_params import Metadata, Reasoning

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

    class CommonIntegratedParams(RequestOptions):
        model: NotRequired[str]
        searchContext: NotRequired[List["Integrated.SearchResult"]]
        chatId: str
        assistantId: str
        assistantMessageId: str
        userMessageId: str
        startText: NotRequired["str"]
        debugInfo: NotRequired[dict[str, Any]]

    class CreateStream(CommonIntegratedParams):
        timeout: NotRequired["int"]
        messages: List["Integrated.ChatCompletionRequestMessage"]

    # For further details about the responses parameters, see the OpenAI API documentation.
    # Note that other parameters from openai.resources.responses.Response.create can be passed
    class CreateStreamResponsesOpenaiParams(TypedDict):
        include: NotRequired[list["ResponseIncludable"] | None]
        instructions: NotRequired[str | None]
        max_output_tokens: NotRequired[int | None]
        metadata: NotRequired[Union["Metadata", None]]
        parallel_tool_calls: NotRequired[bool | None]
        temperature: NotRequired[float | None]
        text: NotRequired["ResponseTextConfigParam"]
        tool_choice: NotRequired["response_create_params.ToolChoice"]
        tools: NotRequired[list["ToolParam"]]
        top_p: NotRequired[float | None]
        reasoning: NotRequired["Reasoning"]

    class CreateStreamResponsesParams(CommonIntegratedParams):
        input: Union[str, "ResponseInputParam"]
        options: NotRequired["Integrated.CreateStreamResponsesOpenaiParams"]

    class ToolCall(TypedDict):
        id: str
        name: str | None
        arguments: str | None

    class ResponsesStreamResult(TypedDict):
        id: str
        message: Message
        toolCalls: List["Integrated.ToolCall"]
        output: list["ResponseOutputItem"]

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
        **params: Unpack["Integrated.CreateStreamResponsesParams"],
    ) -> "Integrated.ResponsesStreamResult":
        """
        Executes a call to the language model and streams to the chat in real-time.
        It automatically inserts references that are mentioned by the model.
        In the form of [sourceX]. The reference documents must be given as a list in searchContext.
        """
        return cast(
            "Integrated.ResponsesStreamResult",
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
        **params: Unpack["Integrated.CreateStreamResponsesParams"],
    ) -> "Integrated.ResponsesStreamResult":
        """
        Executes a call to the language model and streams to the chat in real-time.
        It automatically inserts references that are mentioned by the model.
        In the form of [sourceX]. The reference documents must be given as a list in searchContext.
        """
        return cast(
            "Integrated.ResponsesStreamResult",
            cls._static_request(
                "post",
                "/integrated/chat/stream-responses",
                user_id,
                company_id,
                params,
            ),
        )
