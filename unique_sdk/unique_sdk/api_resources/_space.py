from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    cast,
)

from typing_extensions import NotRequired, TypedDict, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Space(APIResource["Space"]):
    OBJECT_NAME: ClassVar[Literal["space"]] = "space"

    class CreateMessageParams(RequestOptions):
        """
        Parameters for querying the assistant for a message.
        """

        chatId: NotRequired[Optional[str]]
        assistantId: str
        text: NotRequired[Optional[str]]
        toolChoices: NotRequired[Optional[List[str]]]
        scopeRules: NotRequired[Optional[Dict]]

    class Reference(TypedDict):
        """
        Reference information for a message.
        """

        name: str
        url: Optional[str]
        sequenceNumber: int
        originalIndex: Optional[List[int]]
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
        explanation: Optional[str]
        label: Optional[str]
        type: Optional[str]
        title: Optional[str]
        companyId: str
        userId: str
        isVisible: bool
        createdBy: Optional[str]

    class Message(TypedDict):
        """
        Represents a message in the space.
        """

        id: str
        chatId: str
        text: Optional[str]
        originalText: Optional[str]
        role: Literal["system", "user", "assistant"]
        debugInfo: Optional[Dict[str, Any]]
        completedAt: Optional[str]
        createdAt: Optional[str]
        updatedAt: Optional[str]
        stoppedStreamingAt: Optional[str]
        references: Optional[List["Space.Reference"]]
        assessment: Optional[List["Space.Assessment"]]

    class DeleteChatResponse(TypedDict):
        """
        Response for deleting a chat in a space.
        """

        chat_id: str

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
