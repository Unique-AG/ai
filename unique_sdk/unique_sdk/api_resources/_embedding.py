from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from typing_extensions import Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty

if TYPE_CHECKING:
    from unique_sdk._client import _BaseClient


class Embeddings(APIResource["Embeddings"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["openai.embeddings"]:
        return "openai.embeddings"

    class CreateParams(RequestOptions):
        texts: list[str]

    embeddings: list[list[float]]

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
        **params: Unpack["Embeddings.CreateParams"],
    ) -> "Embeddings":
        return cast(
            "Embeddings",
            cls._static_request(
                "post",
                "/openai/embeddings",
                user_id,
                company_id=company_id,
                params=params,
                client=client,
            ),
        )

    @classmethod
    async def create_async(
        cls,
        user_id: str,
        company_id: str,
        client: "_BaseClient | None" = None,
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
                client=client,
            ),
        )
