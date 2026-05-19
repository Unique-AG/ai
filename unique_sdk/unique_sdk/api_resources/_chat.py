from typing import (
    Literal,
    NotRequired,
    TypedDict,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._util import classproperty


class Chat(APIResource["Chat"]):
    """Minimal Chat metadata, exposed by the public API for the SI agent.

    Only fields we have a stable use case for live here:
    - ``id`` / ``title`` -- identity + UI label.
    - ``assistantId`` -- the Space the chat is bound to (nullable for draft
      chats and cross-space project chats).
    - ``projectScopeId`` -- when the chat is anchored to a shared Project
      folder (``share-artifact`` workflow). The SI agent uses this to
      decide reuse / expand / fork when sharing another artifact from the
      same chat.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["chat"]:
        return "chat"

    class ChatInfo(TypedDict):
        id: str
        title: NotRequired[str | None]
        assistantId: NotRequired[str | None]
        projectScopeId: NotRequired[str | None]
        userId: str
        companyId: str
        createdAt: str
        updatedAt: str

    id: str
    title: str | None
    assistantId: str | None
    projectScopeId: str | None
    userId: str
    companyId: str
    createdAt: str
    updatedAt: str

    @classmethod
    def get_info(
        cls,
        user_id: str,
        company_id: str,
        chat_id: str,
    ) -> "Chat.ChatInfo":
        """Fetch the public chat record for ``chat_id``.

        Calls ``GET /chats/{chat_id}``. The chat must belong to the caller
        (``user_id``); otherwise the server returns ``404`` (intentionally
        opaque, so we don't leak the existence of someone else's chats).
        """
        return cast(
            "Chat.ChatInfo",
            cls._static_request(
                "get",
                f"/chats/{chat_id}",
                user_id,
                company_id,
            ),
        )

    @classmethod
    async def get_info_async(
        cls,
        user_id: str,
        company_id: str,
        chat_id: str,
    ) -> "Chat.ChatInfo":
        """Async variant of :meth:`get_info`."""
        return cast(
            "Chat.ChatInfo",
            await cls._static_request_async(
                "get",
                f"/chats/{chat_id}",
                user_id,
                company_id,
            ),
        )
