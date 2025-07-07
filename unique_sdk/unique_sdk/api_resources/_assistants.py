from typing import (
    Any,
    ClassVar,
    List,
    Literal,
    NotRequired,
    TypedDict,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Assistants(APIResource["Assistants"]):
    OBJECT_NAME: ClassVar[Literal["openai.assistant"]] = "openai.assistant"

    class CreateParams(RequestOptions):
        name: str
        instructions: str
        model: NotRequired[
            Literal[
                "AZURE_o4_MINI_2025_0416",
                "AZURE_o3_2025_0416",
            ]
        ]

    class CreateThreadParams(RequestOptions):
        messages: List[Any]

    class Thread(TypedDict):
        id: str

    class CreateMessageParams(RequestOptions):
        content: Any
        role: Literal["user", "assistant"]

    class Message(TypedDict):
        id: str
        content: Any
        role: Literal["user", "assistant"]

    class CreateRunParams(RequestOptions):
        assistant_id: str
        model: NotRequired[
            Literal[
                "AZURE_o4_MINI_2025_0416",
                "AZURE_o3_2025_0416",
            ]
        ]

    class Run(TypedDict):
        id: str
        model: NotRequired[
            Literal[
                "AZURE_o4_MINI_2025_0416",
                "AZURE_o3_2025_0416",
            ]
        ]

    @classmethod
    def create(
        cls,
        company_id: str,
        user_id: str,
        **params: Unpack["Assistants.CreateParams"],
    ) -> "Assistants":
        return cast(
            Assistants,
            cls._static_request(
                "post",
                "/openai/assistants",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        company_id: str,
        user_id: str,
        **params: Unpack["Assistants.CreateParams"],
    ) -> "Assistants":
        return cast(
            Assistants,
            await cls._static_request_async(
                "post",
                "/openai/assistants",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    def create_thread(
        cls,
        company_id: str,
        user_id: str,
        **params: Unpack["Assistants.CreateThreadParams"],
    ) -> "Assistants.Thread":
        return cast(
            Assistants.Thread,
            cls._static_request(
                "post",
                "/openai/threads",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_thread_async(
        cls,
        company_id: str,
        user_id: str,
        **params: Unpack["Assistants.CreateThreadParams"],
    ) -> "Assistants.Thread":
        return cast(
            Assistants.Thread,
            await cls._static_request_async(
                "post",
                "/openai/threads",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    def create_message(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        **params: Unpack["Assistants.CreateMessageParams"],
    ) -> "Assistants.Message":
        return cast(
            Assistants.Message,
            cls._static_request(
                "post",
                f"/openai/threads/{thread_id}/messages",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_message_async(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        **params: Unpack["Assistants.CreateMessageParams"],
    ) -> "Assistants.Message":
        return cast(
            Assistants.Message,
            await cls._static_request_async(
                "post",
                f"/openai/threads/{thread_id}/messages",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    def create_run(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        **params: Unpack["Assistants.CreateRunParams"],
    ) -> "Assistants.Run":
        return cast(
            Assistants.Run,
            cls._static_request(
                "post",
                f"/openai/threads/{thread_id}/runs",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_run_async(
        cls,
        company_id: str,
        user_id: str,
        thread_id: str,
        **params: Unpack["Assistants.CreateRunParams"],
    ) -> "Assistants.Run":
        return cast(
            Assistants.Run,
            await cls._static_request_async(
                "post",
                f"/openai/threads/{thread_id}/runs",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )
