from typing import (
    ClassVar,
    Literal,
    NotRequired,
    Unpack,
    cast,
)

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Assistants(APIResource["Assistants"]):
    OBJECT_NAME: ClassVar[Literal["openai.assistant"]] = "openai.assistant"

    class CreateParams(RequestOptions):
        # expand the input type to allow more complex structures. e.g.: image or file inputs
        name: str
        instructions: str
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
        user_id: str | None = None,
        **params: Unpack["Assistants.CreateParams"],
    ) -> "Assistants":
        return cast(
            Assistants,
            cls._static_request(
                "post",
                "/openai/assistant",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        company_id: str,
        user_id: str | None = None,
        **params: Unpack["Assistants.CreateParams"],
    ) -> "Assistants":
        return cast(
            Assistants,
            await cls._static_request_async(
                "post",
                "/openai/assistant",
                company_id=company_id,
                user_id=user_id,
                params=params,
            ),
        )
