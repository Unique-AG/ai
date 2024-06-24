from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    cast,
    overload,
)
from urllib.parse import quote_plus

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._list_object import ListObject
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import class_method_variant


class Message(APIResource["Message"]):
    """
    This object represents a chat message. Use it to answer user prompts with a generated assistant message.
    """

    OBJECT_NAME: ClassVar[Literal["message"]] = "message"

    class Reference(TypedDict):
        name: str
        url: Optional[str]
        sequenceNumber: int
        sourceId: str
        source: str

    class CreateParams(RequestOptions):
        chatId: str
        assistantId: str
        role: Literal["ASSISTANT"]
        text: NotRequired["str"]
        references: Optional[List["Message.Reference"]]
        debugInfo: Optional[Dict[str, Any]]

    class ModifyParams(RequestOptions):
        chatId: str
        text: NotRequired["str"]
        references: Optional[List["Message.Reference"]]
        debugInfo: Optional[Dict[str, Any]]

    class DeleteParams(RequestOptions):
        chatId: str

    class ListParams(RequestOptions):
        chatId: str

    class RetrieveParams(RequestOptions):
        chatId: str

    chatId: str
    text: Optional[str]
    role: Literal["SYSTEM", "USER", "ASSISTANT"]
    gptRequest: Optional[Dict[str, Any]]
    debugInfo: Optional[Dict[str, Any]]

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
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Message.CreateParams"],
    ) -> "Message":
        """
        Creates a new message object.
        """
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
    def delete(
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
    def delete(  # pyright: ignore[reportGeneralTypeIssues]
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
