from typing import (
    Any,
    ClassVar,
    Dict,
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


class Space(APIResource["Space"]):
    OBJECT_NAME: ClassVar[Literal["space"]] = "space"

    class CreateMessageParams(RequestOptions):
        """
        Parameters for querying the assistant for a message.
        """

        chatId: NotRequired[str | None]
        assistantId: str
        text: NotRequired[str | None]
        toolChoices: NotRequired[List[str] | None]
        scopeRules: NotRequired[dict | None]

    class GetChatMessagesParams(RequestOptions):
        """
        Parameters for getting chat messages.
        """

        skip: NotRequired[int]
        take: NotRequired[int]

    class Reference(TypedDict):
        """
        Reference information for a message.
        """

        name: str
        description: Optional[str]
        url: Optional[str]
        sequenceNumber: int
        originalIndex: Optional[list[int]]
        sourceId: str
        source: str

    class Assessment(TypedDict):
        """
        Assessment information for a message.
        """

        id: str
        createdAt: str
        updatedAt: str
        messageId: str
        status: str
        explanation: str | None
        label: str | None
        type: str | None
        title: str | None
        companyId: str
        userId: str
        isVisible: bool
        createdBy: str | None

    class Message(TypedDict):
        """
        Represents a message in the space.
        """

        id: str
        chatId: str
        text: str | None
        originalText: str | None
        role: Literal["SYSTEM", "USER", "ASSISTANT"]
        debugInfo: Optional[Dict[str, Any]]
        completedAt: str | None
        createdAt: str | None
        updatedAt: str | None
        stoppedStreamingAt: str | None
        references: Optional[List["Space.Reference"]]
        assessment: Optional[List["Space.Assessment"]]

    class DeleteChatResponse(TypedDict):
        """
        Response for deleting a chat in a space.
        """

        chat_id: str

    class GetAllMessagesResponse(TypedDict):
        """
        Response for getting all messages in a chat.
        """

        messages: List["Space.Message"]
        totalCount: int

    class AssistantMcpServer(TypedDict):
        """
        Represents an MCP server associated with an assistant.
        """

        id: str
        name: str
        assistantId: str
        mcpServerId: str
        isEnabled: bool
        createdAt: str
        updatedAt: str

    class Module(TypedDict):
        """
        Represents a module configured for a space.
        """

        id: str
        name: str
        description: Optional[str]
        toolDefinition: Optional[Dict[str, Any]]
        configuration: Dict[str, Any]
        assistantId: str
        weight: int
        isExternal: bool
        isCustomInstructionEnabled: bool
        moduleTemplateId: Optional[str]
        createdAt: str
        updatedAt: str

    class ScopeRule(TypedDict):
        """
        Represents a scope rule for a space.
        """

        id: str
        assistantId: str
        title: str
        companyId: str
        rule: Dict[str, Any]
        isAdvanced: bool
        createdAt: str
        updatedAt: str

    class AssistantAccess(TypedDict):
        """
        Represents access control for a space.
        """

        id: str
        entityId: str
        entityType: str
        type: str

    id: str
    name: str
    defaultForCompanyId: Optional[str]
    title: Optional[str]
    subtitle: Optional[str]
    explanation: Optional[str]
    alert: Optional[str]
    inputLimit: Optional[int]
    inputPlaceholder: Optional[str]
    chatUpload: str
    goals: List[str]
    languageModel: Optional[str]
    fallbackModule: str
    access: List[str]
    isExternal: bool
    isPinned: bool
    uiType: str
    settings: Optional[Dict[str, Any]]
    assistantMcpServers: List["Space.AssistantMcpServer"]
    modules: List["Space.Module"]
    scopeRules: List["Space.ScopeRule"]
    assistantAccess: List["Space.AssistantAccess"]
    createdAt: str
    updatedAt: str

    @classmethod
    def create_message(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Space.CreateMessageParams"],
    ) -> "Space.Message":
        """
        Send a message in a space.
        """
        params["toolChoices"] = params.get("toolChoices") or []
        return cast(
            "Space.Message",
            cls._static_request(
                "post",
                "/space/message",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_message_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Space.CreateMessageParams"],
    ) -> "Space.Message":
        """
        Async send a message in a space.
        """
        params["toolChoices"] = params.get("toolChoices") or []
        return cast(
            "Space.Message",
            await cls._static_request_async(
                "post",
                "/space/message",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def get_chat_messages(
        cls,
        user_id: str,
        company_id: str,
        chat_id: str,
        **params: Unpack["Space.GetChatMessagesParams"],
    ) -> "Space.GetAllMessagesResponse":
        """
        Get all messages in a space chat.
        """
        return cast(
            "Space.GetAllMessagesResponse",
            cls._static_request(
                "get",
                f"/space/chat/{chat_id}/messages",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def get_chat_messages_async(
        cls,
        user_id: str,
        company_id: str,
        chat_id: str,
        **params: Unpack["Space.GetChatMessagesParams"],
    ) -> "Space.GetAllMessagesResponse":
        """
        Async get all messages in a space chat.
        """
        return cast(
            "Space.GetAllMessagesResponse",
            await cls._static_request_async(
                "get",
                f"/space/chat/{chat_id}/messages",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def get_latest_message(
        cls, user_id: str, company_id: str, chat_id: str
    ) -> "Space.Message":
        """
        Get the latest message in a space.
        """
        return cast(
            "Space.Message",
            cls._static_request(
                "get",
                f"/space/{chat_id}/messages/latest",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def get_latest_message_async(
        cls, user_id: str, company_id: str, chat_id: str
    ) -> "Space.Message":
        """
        Async get the latest message in a space.
        """
        return cast(
            "Space.Message",
            await cls._static_request_async(
                "get",
                f"/space/{chat_id}/messages/latest",
                user_id,
                company_id,
            ),
        )

    @classmethod
    def delete_chat(
        cls,
        user_id: str,
        company_id: str,
        chat_id: str,
    ) -> "Space.DeleteChatResponse":
        """
        Delete a chat in a space.
        """
        return cast(
            "Space.DeleteChatResponse",
            cls._static_request(
                "delete",
                f"/space/chat/{chat_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def delete_chat_async(
        cls,
        user_id: str,
        company_id: str,
        chat_id: str,
    ) -> "Space.DeleteChatResponse":
        """
        Async delete a chat in a space.
        """
        return cast(
            "Space.DeleteChatResponse",
            await cls._static_request_async(
                "delete",
                f"/space/chat/{chat_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    def get_space(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
    ) -> "Space":
        """
        Get detailed information about a space (assistant).
        """
        return cast(
            "Space",
            cls._static_request(
                "get",
                f"/space/{space_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def get_space_async(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
    ) -> "Space":
        """
        Async get detailed information about a space (assistant).
        """
        return cast(
            "Space",
            await cls._static_request_async(
                "get",
                f"/space/{space_id}",
                user_id,
                company_id,
            ),
        )
