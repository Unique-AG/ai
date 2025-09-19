from typing import ClassVar, Literal, NotRequired, Unpack, cast

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
        secondsRemaining: NotRequired[int | None]
        percentageCompleted: NotRequired[int | None]

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
        secondsRemaining: NotRequired[int | None]
        percentageCompleted: NotRequired[int | None]

    messageExecutionId: str | None
    messageId: str | None
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]
    type: Literal["DEEP_RESEARCH"] = "DEEP_RESEARCH"
    secondsRemaining: int | None
    percentageCompleted: int | None
    createdAt: str
    updatedAt: str | None

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
