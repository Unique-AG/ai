from typing import Any, ClassVar, Dict, List, Literal, Optional, TypedDict, Unpack, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Space(APIResource["Space"]):
    OBJECT_NAME: ClassVar[Literal["space"]] = "space"

    class CreateMessageParams(RequestOptions):
        """
        Parameters for querying the assistant for a message.
        """

        chatId: str | None = None
        assistantId: str
        text: str | None = None
        toolChoices: List[str] = None
        scopeRules: dict | None = None

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
        text: str | None = None
        originalText: str | None = None
        role: Literal["system", "user", "assistant"]
        debugInfo: Optional[Dict[str, Any]] = None
        completedAt: str | None
        createdAt: str | None
        updatedAt: str | None
        stoppedStreamingAt: str | None
        assessment: Optional[List["Space.Reference"]]
        messageAssessment: Optional[List["Space.Assessment"]]

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
    ) -> None:
        """
        Delete a chat in a space.
        """
        cls._static_request(
            "delete",
            f"/space/chat/{chat_id}",
            user_id,
            company_id,
        )

    @classmethod
    async def delete_chat_async(
        cls,
        user_id: str,
        company_id: str,
        chat_id: str,
    ) -> None:
        """
        Async delete a chat in a space.
        """
        await cls._static_request_async(
            "delete",
            f"/space/chat/{chat_id}",
            user_id,
            company_id,
        )
