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

    class GetLLMModelsParams(RequestOptions):
        """
        Parameters for getting available LLM models.
        """

        module: NotRequired[str | None]
        skipCache: NotRequired[bool | None]

    class CreateMessageParams(RequestOptions):
        """
        Parameters for querying the assistant for a message.
        """

        chatId: NotRequired[str | None]
        assistantId: str
        text: NotRequired[str | None]
        toolChoices: NotRequired[List[str] | None]
        scopeRules: NotRequired[dict | None]

    class Reference(TypedDict):
        """
        Reference information for a message.
        """

        name: str
        url: str | None
        sequenceNumber: int
        originalIndex: List[int] | None
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

    class LLMModels(TypedDict):
        """
        Response for getting available LLM models.
        """

        llmModels: List[str]
        object: Literal["llm-models"]

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
    def get_llm_models(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Space.GetLLMModelsParams"],
    ) -> "Space.LLMModels":
        """
        Get available LLM models.
        """
        return cast(
            "Space.LLMModels",
            cls._static_request(
                "get",
                "/space/llm-models",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def get_llm_models_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Space.GetLLMModelsParams"],
    ) -> "Space.LLMModels":
        """
        Async get available LLM models.
        """
        return cast(
            "Space.LLMModels",
            await cls._static_request_async(
                "get",
                "/space/llm-models",
                user_id,
                company_id,
                params=params,
            ),
        )
