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

    class FileSearchRankingOptions(TypedDict):
        score_threshold: float

    class FileSearch(TypedDict):
        max_num_results: int | None = None
        ranking_options: Optional["Assistants.FileSearchRankingOptions"] = None

    class FunctionDefinition(TypedDict):
        name: str
        description: str | None = None
        parameters: Optional[Dict[str, Any]] = None
        strict: bool | None

    class FileSearchTool(TypedDict):
        type: Literal["file_search"]
        file_search: Optional["Assistants.FileSearch"] = None

    class FunctionTool(TypedDict):
        type: Literal["function"]
        function: "Assistants.FunctionDefinition"

    ToolDefinition = Union[
        CodeInterpreterTool,
        FileSearchTool,
        FunctionTool,
    ]

    class CodeInterpreterResources(TypedDict):
        file_ids: List[str] | None = None

    class FileSearchResources(TypedDict):
        vector_store_ids: List[str] | None = None

    class ToolResources(TypedDict):
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
        tool_resources: Optional["Assistants.ToolResources"] = None

    class CodeInterpreterToolAttachement(TypedDict):
        type: Literal["code_interpreter"]

    class FileSearchToolAttachement(TypedDict):
        type: Literal["file_search"]

    AttachmentTool = Union[CodeInterpreterToolAttachement, FileSearchToolAttachement]

    class Attachment(TypedDict):
        file_id: str | None = None
        tools: List["Assistants.AttachmentTool"] | None = None

    class File(TypedDict):
        file_id: str

    class FileCitationAnnotation(TypedDict):
        end_index: int
        file_citation: "Assistants.File"
        start_index: int
        text: str
        type: Literal["file_citation"]

    class FilePathAnnotation(TypedDict):
        end_index: int
        file_path: "Assistants.File"
        start_index: int
        text: str
        type: Literal["file_path"]

    Annotation = Union[FileCitationAnnotation, FilePathAnnotation]

    class Text(TypedDict):
        type: Literal["text"]
        annotation: Optional[List["Assistants.Annotation"]] = None

    class TextContentBlock(TypedDict):
        type: Literal["text"]
        text: "Assistants.Text"

    class ImageFile(TypedDict):
        file_id: str
        detail: Literal["high", "auto", "low"] | None = None

    class ImageFileContentBlock(TypedDict):
        type: Literal["image_file"]
        image_file: "Assistants.ImageFile"

    class ImageURL(TypedDict):
        url: str
        detail: Literal["high", "auto", "low"] | None = None

    class ImageURLContentBlock(TypedDict):
        type: Literal["image_url"]
        image_url: "Assistants.ImageURL"

    class RefusalContentBlock(TypedDict):
        type: Literal["refusal"]
        refusal: str

    class TextContentBlockParam(TypedDict):
        type: Literal["text"]
        text: str

    MessageContentTypeParam = Union[
        "Assistants.TextContentBlockParam",
        "Assistants.ImageFileContentBlock",
        "Assistants.ImageURLContentBlock",
    ]

    MessageContent = Union[
        str,
        List[
            Union[
                "Assistants.TextContentBlock",
                "Assistants.ImageFileContentBlock",
                "Assistants.ImageURLContentBlock",
                "Assistants.RefusalContentBlock",
            ]
        ],
    ]

    MessageContentPartParam = Union[
        "Assistants.ImageFileContentBlock",
        "Assistants.ImageURLContentBlock",
        "Assistants.TextContentBlockParam",
    ]

    class CreateMessageParams(RequestOptions):
        content: str | List["Assistants.MessageContentPartParam"]
        role: Literal["user", "assistant"]
        attachments: List["Assistants.Attachment"] | None = None
        metadata: dict | None = None

    class CreateThreadParams(RequestOptions):
        messages: List["Assistants.CreateMessageParams"]
        metadata: dict | None = None
        tool_resources: Optional["Assistants.ToolResources"] = None

    class Thread(TypedDict):
        id: str
        metadata: dict | None = None
        tool_resources: Optional["Assistants.ToolResources"] = None

    class Message(TypedDict):
        id: str
        content: "Assistants.MessageContent"
        role: Literal["user", "assistant"]
        thread_id: str
        run_id: str | None = None
        assistant_id: str | None = None
        attachments: List["Assistants.Attachment"] | None = None
        status: Literal["in_progress", "incomplete", "completed"]
        metadata: dict | None = None

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

    class AssistantToolChoiceFunction(TypedDict):
        name: str

    class AssistantToolChoice(TypedDict):
        type: Literal["function", "file_search", "code_interpreter"]
        function: Optional["Assistants.AssistantToolChoiceFunction"] = None

    AssistantToolChoiceOption = Union[
        Literal["none", "auto", "required"], AssistantToolChoice
    ]

    class Usage(TypedDict):
        completion_tokens: int
        prompt_tokens: int
        total_tokens: int

    class Run(TypedDict):
        id: str
        assistant_id: str
        thread_id: str
        status: str
        model: str
        tools: List["Assistants.ToolDefinition"]
        tool_resources: Optional["Assistants.ToolResources"] = None
        tool_choice: Optional["Assistants.AssistantToolChoiceOption"] = None
        usage: Optional["Assistants.Usage"] = None

    class ListMessagesParams(RequestOptions):
        after: str | None = None
        before: str | None = None
        limit: int | None = None
        order: Literal["asc", "desc"] = "asc"
        run_id: str | None = None

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

    @classmethod
    def retrieve_run(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        run_id: str,
    ) -> "Assistants.Run":
        return cast(
            Assistants.Run,
            cls._static_request(
                "get",
                f"/openai/threads/{thread_id}/runs/{run_id}",
                company_id=company_id,
                user_id=user_id,
            ),
        )

    @classmethod
    async def retrieve_run_async(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        run_id: str,
    ) -> "Assistants.Run":
        return cast(
            Assistants.Run,
            await cls._static_request_async(
                "get",
                f"/openai/threads/{thread_id}/runs/{run_id}",
                company_id=company_id,
                user_id=user_id,
            ),
        )

    @classmethod
    def list_messages(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        **params: Unpack["Assistants.ListMessagesParams"],
    ) -> List["Assistants.Message"]:
        return cast(
            List[Assistants.Message],
            cls._static_request(
                "get",
                f"/openai/threads/{thread_id}/messages",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def list_messages_async(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        **params: Unpack["Assistants.ListMessagesParams"],
    ) -> List["Assistants.Message"]:
        return cast(
            List[Assistants.Message],
            await cls._static_request_async(
                "get",
                f"/openai/threads/{thread_id}/messages",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )
