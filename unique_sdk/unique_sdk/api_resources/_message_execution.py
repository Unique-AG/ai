from typing import ClassVar, Literal, Optional, cast

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class MessageExecution(APIResource["MessageExecution"]):
    OBJECT_NAME: ClassVar[Literal["message_execution"]] = "message_execution"
    RESOURCE_URL = "/message-execution"

    class CreateMessageExecutionParams(RequestOptions):
        """
        Parameters for creating a message execution.
        """

        messageId: str
        chatId: str
        type: Literal["DEEP_RESEARCH"]
        secondsRemaining: NotRequired[Optional[int]]
        percentageCompleted: NotRequired[Optional[int]]

    class GetMessageExecutionParams(RequestOptions):
        """
        Parameters for getting a message execution.
        """

        messageId: str

    class UpdateMessageExecutionParams(RequestOptions):
        """
        Parameters for updating a message execution.
        """

        messageId: str
        status: Literal["COMPLETED", "FAILED"]
        secondsRemaining: NotRequired[Optional[int]]
        percentageCompleted: NotRequired[Optional[int]]

    messageExecutionId: Optional[str]
    messageId: Optional[str]
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
    type: Literal["DEEP_RESEARCH"] = "DEEP_RESEARCH"
    secondsRemaining: Optional[int]
    percentageCompleted: Optional[int]
    createdAt: str
    updatedAt: Optional[str]

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageExecution.CreateMessageExecutionParams"],
    ) -> "MessageExecution":
        """
        Create a MessageExecution.
        """
        return cast(
            "MessageExecution",
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
        **params: Unpack["MessageExecution.CreateMessageExecutionParams"],
    ) -> "MessageExecution":
        """
        Async create a MessageExecution.
        """
        return cast(
            "MessageExecution",
            await cls._static_request_async(
                "post",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def get(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageExecution.GetMessageExecutionParams"],
    ) -> "MessageExecution":
        """
        Get a MessageExecution by its ID.
        """
        return cast(
            "MessageExecution",
            cls._static_request(
                "get", cls.RESOURCE_URL, user_id, company_id, params=params
            ),
        )

    @classmethod
    async def get_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageExecution.GetMessageExecutionParams"],
    ) -> "MessageExecution":
        """
        Async get a MessageExecution by its ID.
        """
        return cast(
            "MessageExecution",
            await cls._static_request_async(
                "get", cls.RESOURCE_URL, user_id, company_id, params=params
            ),
        )

    @classmethod
    def update(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["MessageExecution.UpdateMessageExecutionParams"],
    ) -> "MessageExecution":
        """
        Update a MessageExecution.
        """
        return cast(
            "MessageExecution",
            cls._static_request(
                "patch",
                cls.RESOURCE_URL,
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
        **params: Unpack["MessageExecution.UpdateMessageExecutionParams"],
    ) -> "MessageExecution":
        """
        Async update a MessageExecution.
        """
        return cast(
            "MessageExecution",
            await cls._static_request_async(
                "patch",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params=params,
            ),
        )
