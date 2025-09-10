from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    NotRequired,
    Optional,
    TypedDict,
    Union,
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

    class FunctionDefinition(TypedDict, total=False):
        name: str
        description: Optional[str]
        parameters: Optional[Dict[str, Any]]

    class ChatCompletionsFunctionToolDefinition(TypedDict):
        type: Literal["function"]
        function: "ChatCompletion.FunctionDefinition"

    class FunctionName(TypedDict):
        name: str

    class ChatCompletionsNamedFunctionToolSelectionName(TypedDict):
        name: str

    class ChatCompletionsNamedFunctionToolSelection(TypedDict):
        type: Literal["function"]
        function: "ChatCompletion.ChatCompletionsNamedFunctionToolSelectionName"

    class ChatCompletionsTextResponseFormat(TypedDict, total=False):
        type: Literal["text", "json_schema"]
        json_schema: dict

    class Options(TypedDict, total=False):
        functions: NotRequired[List["ChatCompletion.FunctionDefinition"]]
        reasoningEffort: NotRequired[Literal["low", "medium", "high", None]]
        functionCall: NotRequired[
            Union[Literal["auto", "none"], "ChatCompletion.FunctionName"]
        ]
        maxTokens: NotRequired[int]
        temperature: NotRequired[float]
        topP: NotRequired[float]
        logitBias: NotRequired[Dict[str, float]]
        user: NotRequired[str]
        n: NotRequired[int]
        stop: NotRequired[List[str]]
        presencePenalty: NotRequired[float]
        frequencyPenalty: NotRequired[float]
        seed: NotRequired[int]
        responseFormat: NotRequired["ChatCompletion.ChatCompletionsTextResponseFormat"]
        tools: NotRequired[List["ChatCompletion.ChatCompletionsFunctionToolDefinition"]]
        toolChoice: NotRequired[
            "ChatCompletion.ChatCompletionsNamedFunctionToolSelection"
        ]

    class CreateParams(RequestOptions):
        model: NotRequired[
            Literal[
                "AZURE_GPT_4_0613",
                "AZURE_GPT_4_32K_0613",
            ]
        ]
        timeout: NotRequired[Optional["int"]]
        messages: List[ChatCompletionRequestMessage]
        options: NotRequired["ChatCompletion.Options"]

    model: Literal[
        "AZURE_GPT_4_0613",
        "AZURE_GPT_4_32K_0613",
    ]
    choices: List[ChatCompletionChoicesInner]

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
