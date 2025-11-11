from typing import ClassVar, Literal, NotRequired, Optional, TypedDict, Unpack, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class MessageLog(APIResource["MessageLog"]):
    OBJECT_NAME: ClassVar[Literal["message_log"]] = "message_log"
    RESOURCE_URL = "/message-log"

    StatusLiteral = Literal["RUNNING", "COMPLETED", "FAILED"]

    class Reference(TypedDict):
        name: str
        description: Optional[str]
        url: Optional[str]
        sequenceNumber: int
        originalIndex: Optional[list[int]]
        sourceId: str
        source: str

    class CreateMessageLogParams(RequestOptions):
        """
        Parameters for creating a message log.
        """

        messageId: str
        text: str
        status: "MessageLog.StatusLiteral"
        order: int
        details: NotRequired[dict | None]
        uncitedReferences: NotRequired[dict | None]
        references: NotRequired[list["MessageLog.Reference"] | None]

    class UpdateMessageLogParams(RequestOptions):
        """
        Parameters for updating a message log.
        """

        text: NotRequired[str | None]
        status: NotRequired["MessageLog.StatusLiteral | None"]
        order: NotRequired[int | None]
        details: NotRequired[dict | None]
        uncitedReferences: NotRequired[dict | None]
        references: NotRequired[list["MessageLog.Reference"] | None]

    id: str
    messageId: str
    status: "MessageLog.StatusLiteral"
    text: str
    details: dict
    uncitedReferences: dict
    order: int
    createdAt: str
    updatedAt: str

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
        # Clean up empty descriptions from references
        if "references" in params and params["references"]:
            for ref in params["references"]:
                if "description" in ref and not ref["description"]:
                    ref.pop("description")

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
        # Clean up empty descriptions from references
        if "references" in params and params["references"]:
            for ref in params["references"]:
                if "description" in ref and not ref["description"]:
                    ref.pop("description")

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
        # Clean up empty descriptions from references
        if "references" in params and params["references"]:
            for ref in params["references"]:
                if "description" in ref and not ref["description"]:
                    ref.pop("description")

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
        # Clean up empty descriptions from references
        if "references" in params and params["references"]:
            for ref in params["references"]:
                if "description" in ref and not ref["description"]:
                    ref.pop("description")

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
