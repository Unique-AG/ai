from typing import Literal, cast

from typing_extensions import Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class Embeddings(APIResource["Embeddings"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["openai.embeddings"]:
        return "openai.embeddings"

    class CreateParams(RequestOptions):
        texts: list[str]

    embeddings: list[list[float]]

    @classmethod
    def create(
        cls, user_id: str, company_id: str, **params: Unpack["Embeddings.CreateParams"]
    ) -> "Embeddings":
        return cast(
            "Embeddings",
            cls._static_request(
                "post",
                "/openai/embeddings",
                user_id,
                company_id=company_id,
                params=params,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Embeddings.CreateParams"],
    ) -> "Embeddings":
        return cast(
            "Embeddings",
            await cls._static_request_async(
                "post",
                "/openai/embeddings",
                user_id,
                company_id=company_id,
                params=params,
            ),
        )
