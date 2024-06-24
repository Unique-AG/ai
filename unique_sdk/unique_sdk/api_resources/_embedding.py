from typing import ClassVar, List, Literal, cast

from typing_extensions import Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class Embeddings(APIResource["Embeddings"]):
    OBJECT_NAME: ClassVar[Literal["openai.embeddings"]] = "openai.embeddings"

    class CreateParams(RequestOptions):
        texts: List[str]

    embeddings: List[List[float]]

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
