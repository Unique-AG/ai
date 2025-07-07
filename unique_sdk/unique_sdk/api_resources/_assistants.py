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


class Assistants(APIResource["Assistants"]):
    OBJECT_NAME: ClassVar[Literal["openai.assistant"]] = "openai.assistant"

    class CodeInterpreterTool(TypedDict):
        type: Literal["code_interpreter"]

    class FileSearchRankingOptions(TypedDict, total=False):
        # Add ranking option fields as needed
        pass

    class FileSearchToolOverrides(TypedDict, total=False):
        max_num_results: int | None = None
        ranking_options: Optional["Assistants.FileSearchRankingOptions"]

    class FunctionToolFunction(TypedDict, total=False):
        name: str
        description: str | None = None
        parameters: Optional[Dict[str, Any]]
        strict: bool | None

    class FileSearchTool(TypedDict, total=False):
        type: Literal["file_search"]
        file_search: Optional["Assistants.FileSearchToolOverrides"]

    class FunctionTool(TypedDict):
        type: Literal["function"]
        function: "Assistants.FunctionToolFunction"

    ToolDefinition = Union[
        CodeInterpreterTool,
        FileSearchTool,
        FunctionTool,
    ]

    class CodeInterpreterResources(TypedDict, total=False):
        file_ids: List[str]

    class FileSearchResources(TypedDict, total=False):
        vector_store_ids: List[str]

    class ToolResources(TypedDict, total=False):
        code_interpreter: Optional["Assistants.CodeInterpreterResources"]
        file_search: Optional["Assistants.FileSearchResources"]

    class CreateParams(RequestOptions):
        name: str
        instructions: str
        model: NotRequired[
            Literal[
                "AZURE_o4_MINI_2025_0416",
                "AZURE_o3_2025_0416",
            ]
        ]
        tools: list["Assistants.ToolDefinition"]
        file_ids: list[str]
        metadata: dict | None = None
        description: str | None = None
        temperature: float | None = None
        top_p: float | None = None
        max_tokens: int | None = None
        tool_resources: Optional["Assistants.ToolResources"]

    class CreateThreadParams(RequestOptions):
        messages: List[Any]

    class Thread(TypedDict):
        id: str

    class CreateMessageParams(RequestOptions):
        content: Any
        role: Literal["user", "assistant"]

    class Message(TypedDict):
        id: str
        content: Any
        role: Literal["user", "assistant"]

    class CreateRunParams(RequestOptions):
        assistant_id: str
        model: NotRequired[
            Literal[
                "AZURE_o4_MINI_2025_0416",
                "AZURE_o3_2025_0416",
            ]
        ]

    class Run(TypedDict):
        id: str
        model: NotRequired[
            Literal[
                "AZURE_o4_MINI_2025_0416",
                "AZURE_o3_2025_0416",
            ]
        ]

    @classmethod
    def create(
        cls,
        company_id: str,
        user_id: str,
        **params: Unpack["Assistants.CreateParams"],
    ) -> "Assistants":
        return cast(
            Assistants,
            cls._static_request(
                "post",
                "/openai/assistants",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        company_id: str,
        user_id: str,
        **params: Unpack["Assistants.CreateParams"],
    ) -> "Assistants":
        return cast(
            Assistants,
            await cls._static_request_async(
                "post",
                "/openai/assistants",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    def create_thread(
        cls,
        company_id: str,
        user_id: str,
        **params: Unpack["Assistants.CreateThreadParams"],
    ) -> "Assistants.Thread":
        return cast(
            Assistants.Thread,
            cls._static_request(
                "post",
                "/openai/threads",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_thread_async(
        cls,
        company_id: str,
        user_id: str,
        **params: Unpack["Assistants.CreateThreadParams"],
    ) -> "Assistants.Thread":
        return cast(
            Assistants.Thread,
            await cls._static_request_async(
                "post",
                "/openai/threads",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    def create_message(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        **params: Unpack["Assistants.CreateMessageParams"],
    ) -> "Assistants.Message":
        return cast(
            Assistants.Message,
            cls._static_request(
                "post",
                f"/openai/threads/{thread_id}/messages",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_message_async(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        **params: Unpack["Assistants.CreateMessageParams"],
    ) -> "Assistants.Message":
        return cast(
            Assistants.Message,
            await cls._static_request_async(
                "post",
                f"/openai/threads/{thread_id}/messages",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    def create_run(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        **params: Unpack["Assistants.CreateRunParams"],
    ) -> "Assistants.Run":
        return cast(
            Assistants.Run,
            cls._static_request(
                "post",
                f"/openai/threads/{thread_id}/runs",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_run_async(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        **params: Unpack["Assistants.CreateRunParams"],
    ) -> "Assistants.Run":
        return cast(
            Assistants.Run,
            await cls._static_request_async(
                "post",
                f"/openai/threads/{thread_id}/runs",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )
