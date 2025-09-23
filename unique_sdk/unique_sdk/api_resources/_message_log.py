from typing import (
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


class MessageLog(APIResource["MessageLog"]):
    OBJECT_NAME: ClassVar[Literal["message_log"]] = "message_log"
    RESOURCE_URL = "/message-log"

    class Reference(TypedDict):
        name: str
        url: Optional[str]
        sequenceNumber: int
        originalIndex: Optional[List[int]]
        sourceId: str
        source: str

    class CreateMessageLogParams(RequestOptions):
        """
        Parameters for creating a message log.
        """

        messageId: str
        text: str
        status: Literal["RUNNING", "COMPLETED", "FAILED"]
        order: int
        details: NotRequired[Optional[Dict]]
        uncitedReferences: NotRequired[Optional[Dict]]
        references: NotRequired[Optional[List["MessageLog.Reference"]]]

    class UpdateMessageLogParams(RequestOptions):
        """
        Parameters for updating a message log.
        """

        text: NotRequired[Optional[str]]
        status: NotRequired[Optional[Literal["RUNNING", "COMPLETED", "FAILED"]]]
        order: int
        details: NotRequired[Optional[Dict]]
        uncitedReferences: NotRequired[Optional[Dict]]
        references: NotRequired[Optional[List["MessageLog.Reference"]]]

    messageLogId: Optional[str]
    messageId: Optional[str]
    status: Literal["RUNNING", "COMPLETED", "FAILED"]
    text: Optional[str]
    details: dict
    uncitedReferences: dict
    order: int
    createdAt: str
    updatedAt: Optional[str]

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageLog.CreateMessageLogParams"],
    ) -> "MessageLog":
        """
        Create a MessageLog.
        """
        return cast(
            "MessageLog",
            cls._static_request(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageLog.CreateMessageLogParams"],
    ) -> "MessageLog":
        """
        Async create a MessageLog.
        """
        return cast(
            "MessageLog",
            await cls._static_request_async(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def update(
        cls,
        user_id: str,
        company_id: str,
        message_log_id: str,
        **params: Unpack["MessageLog.UpdateMessageLogParams"],
    ) -> "MessageLog":
        """
        Update a MessageLog.
        """
        return cast(
            "MessageLog",
            cls._static_request(
                "patch",
                f"{cls.RESOURCE_URL}/{message_log_id}",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def update_async(
        cls,
        user_id: str,
        company_id: str,
        message_log_id: str,
        **params: Unpack["MessageLog.UpdateMessageLogParams"],
    ) -> "MessageLog":
        """
        Async update a MessageLog.
        """
        return cast(
            "MessageLog",
            await cls._static_request_async(
                "patch",
                f"{cls.RESOURCE_URL}/{message_log_id}",
                user_id,
                company_id,
                params=params,
            ),
        )
