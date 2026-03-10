from typing import (
    Any,
    ClassVar,
    Literal,
    NotRequired,
    TypeAlias,
    TypedDict,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Space(APIResource["Space"]):
    OBJECT_NAME: ClassVar[Literal["space"]] = "space"

    UiType: TypeAlias = Literal[
        "MAGIC_TABLE", "UNIQUE_CUSTOM", "TRANSLATION", "UNIQUE_AI"
    ]

    class ModuleParams(TypedDict):
        name: str
        description: NotRequired[str | None]
        weight: NotRequired[int | None]
        isExternal: NotRequired[bool | None]
        isCustomInstructionEnabled: NotRequired[bool | None]
        configuration: NotRequired[dict[str, Any] | None]
        toolDefinition: NotRequired[dict[str, Any] | None]

    class UpdateModuleParams(TypedDict):
        moduleId: str
        configuration: NotRequired[dict[str, Any] | None]
        name: NotRequired[str | None]
        description: NotRequired[str | None]
        weight: NotRequired[int | None]

    class CreateSpaceParams(RequestOptions):
        name: str
        fallbackModule: str
        modules: list["Space.ModuleParams"]
        explanation: NotRequired[str | None]
        alert: NotRequired[str | None]
        chatUpload: NotRequired[Literal["ENABLED", "DISABLED"] | None]
        languageModel: NotRequired[str | None]
        isExternal: NotRequired[bool | None]
        isPinned: NotRequired[bool | None]
        uiType: NotRequired["Space.UiType | None"]
        settings: NotRequired[dict[str, Any] | None]

    class UpdateParams(RequestOptions):
        name: NotRequired[str | None]
        title: NotRequired[str | None]
        modules: NotRequired[list["Space.UpdateModuleParams"] | None]
        explanation: NotRequired[str | None]
        alert: NotRequired[str | None]
        chatUpload: NotRequired[Literal["ENABLED", "DISABLED"] | None]
        languageModel: NotRequired[str | None]
        isPinned: NotRequired[bool | None]
        settings: NotRequired[dict[str, Any] | None]
        allowEndUserSpace: NotRequired[bool | None]
        uiType: NotRequired["Space.UiType | None"]

    class AccessEntry(TypedDict):
        entityId: str
        entityType: Literal["USER", "GROUP"]
        type: Literal["USE", "MANAGE", "UPLOAD"]

    class AddSpaceAccessParams(RequestOptions):
        access: list["Space.AccessEntry"]

    class DeleteSpaceAccessParams(RequestOptions):
        accessIds: list[str]

    class Correlation(TypedDict):
        parentMessageId: str
        parentChatId: str
        parentAssistantId: str

    class CreateMessageParams(RequestOptions):
        """
        Parameters for querying the assistant for a message.
        """

        chatId: NotRequired[str | None]
        assistantId: str
        text: NotRequired[str | None]
        toolChoices: NotRequired[list[str] | None]
        scopeRules: NotRequired[dict[str, Any] | None]
        correlation: NotRequired["Space.Correlation | None"]

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
        description: str | None
        url: str | None
        sequenceNumber: int
        originalIndex: list[int] | None
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
        debugInfo: dict[str, Any] | None
        gptRequest: dict[str, Any] | None
        completedAt: str | None
        createdAt: str | None
        updatedAt: str | None
        startedStreamingAt: str | None
        stoppedStreamingAt: str | None
        references: list["Space.Reference"] | None
        assessment: list["Space.Assessment"] | None

    class DeleteChatResponse(TypedDict):
        """
        Response for deleting a chat in a space.
        """

        chat_id: str

    class GetAllMessagesResponse(TypedDict):
        """
        Response for getting all messages in a chat.
        """

        messages: list["Space.Message"]
        totalCount: int

    class McpServer(TypedDict):
        """
        Represents an MCP server associated with a space.
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
        description: str | None
        toolDefinition: dict[str, Any] | None
        configuration: dict[str, Any]
        assistantId: str
        weight: int
        isExternal: bool
        isCustomInstructionEnabled: bool
        moduleTemplateId: str | None
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
        rule: dict[str, Any]
        isAdvanced: bool
        createdAt: str
        updatedAt: str

    class Access(TypedDict):
        id: str
        entityId: str
        entityType: str
        type: str

    class SpaceAccessResponse(TypedDict):
        access: list["Space.Access"]

    class DeleteSpaceAccessResponse(TypedDict):
        success: bool

    class DeleteSpaceResponse(TypedDict):
        id: str

    id: str
    name: str
    defaultForCompanyId: str | None
    title: str | None
    subtitle: str | None
    explanation: str | None
    alert: str | None
    inputLimit: int | None
    inputPlaceholder: str | None
    chatUpload: str
    goals: list[str]
    languageModel: str | None
    fallbackModule: str
    access: list[str]
    isExternal: bool
    isPinned: bool
    uiType: str
    settings: dict[str, Any] | None
    assistantMcpServers: list["Space.McpServer"]
    modules: list["Space.Module"]
    scopeRules: list["Space.ScopeRule"]
    assistantAccess: list["Space.Access"]
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

    @classmethod
    def create_space(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Space.CreateSpaceParams"],
    ) -> "Space":
        return cast(
            "Space",
            cls._static_request(
                "post",
                "/space",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_space_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Space.CreateSpaceParams"],
    ) -> "Space":
        return cast(
            "Space",
            await cls._static_request_async(
                "post",
                "/space",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def get_space_access(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
    ) -> "Space.SpaceAccessResponse":
        return cast(
            "Space.SpaceAccessResponse",
            cls._static_request(
                "get",
                f"/space/{space_id}/access",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def get_space_access_async(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
    ) -> "Space.SpaceAccessResponse":
        return cast(
            "Space.SpaceAccessResponse",
            await cls._static_request_async(
                "get",
                f"/space/{space_id}/access",
                user_id,
                company_id,
            ),
        )

    @classmethod
    def add_space_access(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
        **params: Unpack["Space.AddSpaceAccessParams"],
    ) -> "Space.SpaceAccessResponse":
        return cast(
            "Space.SpaceAccessResponse",
            cls._static_request(
                "post",
                f"/space/{space_id}/access",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def add_space_access_async(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
        **params: Unpack["Space.AddSpaceAccessParams"],
    ) -> "Space.SpaceAccessResponse":
        return cast(
            "Space.SpaceAccessResponse",
            await cls._static_request_async(
                "post",
                f"/space/{space_id}/access",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def delete_space_access(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
        **params: Unpack["Space.DeleteSpaceAccessParams"],
    ) -> "Space.DeleteSpaceAccessResponse":
        return cast(
            "Space.DeleteSpaceAccessResponse",
            cls._static_request(
                "delete",
                f"/space/{space_id}/access",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def delete_space_access_async(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
        **params: Unpack["Space.DeleteSpaceAccessParams"],
    ) -> "Space.DeleteSpaceAccessResponse":
        return cast(
            "Space.DeleteSpaceAccessResponse",
            await cls._static_request_async(
                "delete",
                f"/space/{space_id}/access",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def update_space(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
        **params: Unpack["Space.UpdateParams"],
    ) -> "Space":
        return cast(
            "Space",
            cls._static_request(
                "patch",
                f"/space/{space_id}",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def update_space_async(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
        **params: Unpack["Space.UpdateParams"],
    ) -> "Space":
        return cast(
            "Space",
            await cls._static_request_async(
                "patch",
                f"/space/{space_id}",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def delete_space(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
    ) -> "Space.DeleteSpaceResponse":
        """
        Delete a space.
        """
        return cast(
            "Space.DeleteSpaceResponse",
            cls._static_request(
                "delete",
                f"/space/{space_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def delete_space_async(
        cls,
        user_id: str,
        company_id: str,
        space_id: str,
    ) -> "Space.DeleteSpaceResponse":
        """
        Async delete a space.
        """
        return cast(
            "Space.DeleteSpaceResponse",
            await cls._static_request_async(
                "delete",
                f"/space/{space_id}",
                user_id,
                company_id,
            ),
        )
