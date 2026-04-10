from datetime import datetime
from typing import (
    Any,
    Literal,
    NotRequired,
    TypedDict,
    Unpack,
    cast,
    overload,
)
from urllib.parse import quote_plus

from unique_sdk._api_resource import APIResource
from unique_sdk._list_object import ListObject
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import class_method_variant, classproperty


class Message(APIResource["Message"]):
    """
    This object represents a chat message. Use it to answer user prompts with a generated assistant message.
    """

    @classproperty
    def OBJECT_NAME(cls) -> Literal["message"]:
        return "message"

    class Reference(TypedDict):
        name: str
        sequenceNumber: int
        sourceId: str
        source: str
        description: NotRequired[str | None]
        url: NotRequired[str | None]
        originalIndex: NotRequired[list[int] | None]

    class Assessment(TypedDict):
        """Assessment row attached to a message."""

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

    class Correlation(TypedDict):
        parentMessageId: str
        parentChatId: str
        parentAssistantId: str

    class CreateParams(RequestOptions):
        chatId: str
        assistantId: str
        role: Literal["ASSISTANT", "USER"]
        text: NotRequired[str | None]
        references: NotRequired[list["Message.Reference"] | None]
        gptRequest: NotRequired[dict[str, Any] | None]
        debugInfo: NotRequired[dict[str, Any] | None]
        completedAt: NotRequired[datetime | None]
        correlation: NotRequired["Message.Correlation | None"]

    class ModifyParams(RequestOptions):
        chatId: str
        originalText: NotRequired[str | None]
        text: NotRequired[str | None]
        references: NotRequired[list["Message.Reference"] | None]
        gptRequest: NotRequired[dict[str, Any] | None]
        debugInfo: NotRequired[dict[str, Any] | None]
        startedStreamingAt: NotRequired[datetime | None]
        stoppedStreamingAt: NotRequired[datetime | None]
        completedAt: NotRequired[datetime | None]

    class DeleteParams(RequestOptions):
        chatId: str

    class ListParams(RequestOptions):
        chatId: str

    class RetrieveParams(RequestOptions):
        chatId: str

    class CreateEventParams(ModifyParams):
        messageId: str

    chatId: str
    text: str | None
    originalText: str | None
    role: Literal["SYSTEM", "USER", "ASSISTANT"]
    gptRequest: dict[str, Any] | None
    debugInfo: dict[str, Any] | None
    completedAt: datetime | None
    createdAt: datetime | None
    updatedAt: datetime | None
    startedStreamingAt: datetime | None
    stoppedStreamingAt: datetime | None
    userAbortedAt: datetime | None
    references: list["Message.Reference"] | None
    assessment: list["Message.Assessment"] | None
    object: str

    @classmethod
    def list(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Message.ListParams"],
    ) -> ListObject["Message"]:
        """
        Returns a list of messages for a given chat.
        """
        result = cls._static_request(
            "get",
            cls.class_url(),
            user_id,
            company_id,
            params=params,
        )

        if not isinstance(result, ListObject):
            raise TypeError(
                "Expected list object from API, got %s" % (type(result).__name__)
            )

        return result

    @classmethod
    async def list_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Message.ListParams"],
    ) -> ListObject["Message"]:
        """
        Returns a list of messages for a given chat.
        """
        result = await cls._static_request_async(
            "get",
            cls.class_url(),
            user_id,
            company_id,
            params=params,
        )

        if not isinstance(result, ListObject):
            raise TypeError(
                "Expected list object from API, got %s" % (type(result).__name__)
            )

        return result

    @classmethod
    def retrieve(
        cls,
        user_id: str,
        company_id: str,
        id: str,
        **params: Unpack["Message.RetrieveParams"],
    ) -> "Message":
        """
        Retrieves a Message object.
        """
        instance = cls(user_id, company_id, id, **params)
        instance.refresh(user_id, company_id)
        return instance

    @classmethod
    async def retrieve_async(
        cls,
        user_id: str,
        company_id: str,
        id: str,
        **params: Unpack["Message.RetrieveParams"],
    ) -> "Message":
        """
        Retrieves a Message object.
        """
        instance = cls(user_id, company_id, id, **params)
        await instance.refresh_async(user_id, company_id)
        return instance

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Message.CreateParams"],
    ) -> "Message":
        """
        Creates a new message object.
        """
        # Clean up empty descriptions from references
        if "references" in params and params["references"]:
            for ref in params["references"]:
                if "description" in ref and not ref["description"]:
                    ref.pop("description")

        return cast(
            "Message",
            cls._static_request(
                "post",
                cls.class_url(),
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Message.CreateParams"],
    ) -> "Message":
        """
        Creates a new message object.
        """
        # Clean up empty descriptions from references
        if "references" in params and params["references"]:
            for ref in params["references"]:
                if "description" in ref and not ref["description"]:
                    ref.pop("description")

        return cast(
            "Message",
            await cls._static_request_async(
                "post",
                cls.class_url(),
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    def modify(
        cls,
        user_id: str,
        company_id: str,
        id: str,
        **params: Unpack["Message.ModifyParams"],
    ) -> "Message":
        """
        Updates an existing message object.
        """
        # Clean up empty descriptions from references
        if "references" in params and params["references"]:
            for ref in params["references"]:
                if "description" in ref and not ref["description"]:
                    ref.pop("description")

        url = "%s/%s" % (cls.class_url(), quote_plus(id))
        return cast(
            "Message",
            cls._static_request(
                "patch",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def modify_async(
        cls,
        user_id: str,
        company_id: str,
        id: str,
        **params: Unpack["Message.ModifyParams"],
    ) -> "Message":
        """
        Updates an existing message object.
        """
        # Clean up empty descriptions from references
        if "references" in params and params["references"]:
            for ref in params["references"]:
                if "description" in ref and not ref["description"]:
                    ref.pop("description")

        url = "%s/%s" % (cls.class_url(), quote_plus(id))
        return cast(
            "Message",
            await cls._static_request_async(
                "patch",
                url,
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    def _cls_delete(
        cls,
        id: str,
        user_id: str,
        company_id: str,
        **params: Unpack["Message.DeleteParams"],
    ) -> "Message":
        """
        Permanently deletes a message. It cannot be undone.
        """
        url = "%s/%s" % (cls.class_url(), quote_plus(id))
        return cast(
            "Message",
            cls._static_request("delete", url, user_id, company_id, params=params),
        )

    @overload
    @staticmethod
    def delete(  # pyright: ignore[reportInconsistentOverload]
        id: str, user_id: str, company_id: str, **params: Unpack["Message.DeleteParams"]
    ) -> "Message":
        """
        Permanently deletes a message. It cannot be undone.
        """
        ...

    @overload
    def delete(
        self, user_id: str, company_id: str, **params: Unpack["Message.DeleteParams"]
    ) -> "Message":
        """
        Permanently deletes a message. It cannot be undone.
        """
        ...

    @class_method_variant("_cls_delete")
    def delete(  # pyright: ignore[reportInconsistentOverload]
        self,
        user_id: str,
        company_id: str,
        **params: Unpack["Message.DeleteParams"],
    ) -> "Message":
        """
        Permanently deletes a message. It cannot be undone.
        """
        return self._request_and_refresh(
            "delete",
            self.instance_url(),
            user_id,
            company_id,
            params=params,
        )

    async def delete_async(
        self,
        user_id: str,
        company_id: str,
        **params: Unpack["Message.DeleteParams"],
    ) -> "Message":
        """
        Permanently deletes a message. It cannot be undone.
        """
        return await self._request_and_refresh_async(
            "delete",
            self.instance_url(),
            user_id,
            company_id,
            params=params,
        )

    @classmethod
    def create_event(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Message.CreateEventParams"],
    ) -> "Message":
        """
        Creates a new message event object.
        """
        # Clean up empty descriptions from references
        if "references" in params and params["references"]:
            for ref in params["references"]:
                if "description" in ref and not ref["description"]:
                    ref.pop("description")

        message_id = params.get("messageId")
        params.pop("messageId", None)
        return cast(
            "Message",
            cls._static_request(
                "post",
                f"{cls.class_url()}/{message_id}/event",
                user_id,
                company_id,
                params,
            ),
        )

    @classmethod
    async def create_event_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Message.CreateEventParams"],
    ) -> "Message":
        """
        Creates a new message event object.
        """
        # Clean up empty descriptions from references
        if "references" in params and params["references"]:
            for ref in params["references"]:
                if "description" in ref and not ref["description"]:
                    ref.pop("description")

        message_id = params.get("messageId")
        params.pop("messageId", None)
        return cast(
            "Message",
            await cls._static_request_async(
                "post",
                f"{cls.class_url()}/{message_id}/event",
                user_id,
                company_id,
                params,
            ),
        )
