from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
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
        ranking_options: Optional["Assistants.FileSearchRankingOptions"] = None

    class FunctionToolFunction(TypedDict, total=False):
        name: str
        description: str | None = None
        parameters: Optional[Dict[str, Any]] = None
        strict: bool | None

    class FileSearchTool(TypedDict, total=False):
        type: Literal["file_search"]
        file_search: Optional["Assistants.FileSearchToolOverrides"] = None

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
        code_interpreter: Optional["Assistants.CodeInterpreterResources"] = None
        file_search: Optional["Assistants.FileSearchResources"] = None

    class CreateParams(RequestOptions):
        name: str
        instructions: str
        model: str
        tools: list["Assistants.ToolDefinition"]
        metadata: dict | None = None
        description: str | None = None
        temperature: float | None = None
        top_p: float | None = None
        max_tokens: int | None = None
        tool_resources: Optional["Assistants.ToolResources"] = None

    class CodeInterpreterToolAttachement(TypedDict):
        type: Literal["code_interpreter"]

    class FileSearchToolAttachement(TypedDict):
        type: Literal["file_search"]

    AttachmentTool = Union[CodeInterpreterToolAttachement, FileSearchToolAttachement]

    class Attachment(TypedDict, total=False):
        file_id: str
        tools: List["Assistants.AttachmentTool"]

    class CreateMessageParams(RequestOptions):
        content: Any
        role: Literal["user", "assistant"]
        attachments: List["Assistants.Attachment"] | None = None
        metadata: dict | None = None

    class CreateThreadParams(RequestOptions):
        messages: List["Assistants.CreateMessageParams"]
        metadata: dict | None = None
        tool_resources: Optional["Assistants.ToolResources"] = None

    class Thread(TypedDict):
        id: str
        tool_resources: Optional["Assistants.ToolResources"] = None

    class Message(TypedDict):
        id: str
        content: Any
        role: Literal["user", "assistant"]
        thread_id: str
        assistant_id: str
        attachments: List["Assistants.Attachment"] | None = None
        status: Literal["in_progress", "incomplete", "completed"]

    class CreateRunParams(RequestOptions):
        assistant_id: str
        model: str

    class ToolChoiceFileSearch(TypedDict):
        type: Literal["file_search"]

    class ToolChoiceFunction(TypedDict):
        type: Literal["function"]
        function: Dict[str, Any]

    ToolChoiceObject = Union[ToolChoiceFileSearch, ToolChoiceFunction]

    ToolChoice = Union[
        Literal["none", "auto", "required"],
        ToolChoiceObject,
    ]

    class Run(TypedDict):
        id: str
        assistant_id: str
        thread_id: str
        status: str
        model: str
        tools: List["Assistants.ToolDefinition"]
        tool_resources: Optional["Assistants.ToolResources"] = None
        tool_choice: Optional["Assistants.ToolChoice"] = None

    id: str
    description: str | None = None
    instructions: str | None = None
    model: str
    metadata: dict | None = None
    name: str
    temperature: float | None = None
    top_p: float | None = None
    tools: List["Assistants.ToolDefinition"]
    tool_resources: Optional["Assistants.ToolResources"] = None

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
