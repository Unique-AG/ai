from typing import List, Literal, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._util import classproperty


class Acronyms(APIResource["Acronyms"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["company.acronyms"]:
        return "company.acronyms"

    Acronyms: List[List[float]]

    @classmethod
    def get(cls, user_id: str, company_id: str) -> "Acronyms":  # pyright: ignore[reportIncompatibleMethodOverride]
        return cast(
            "Acronyms",
            cls._static_request(
                "get",
                "/company/acronyms",
                user_id,
                company_id=company_id,
            ),
        )

    @classmethod
    async def get_async(cls, user_id: str, company_id: str) -> "Acronyms":
        return cast(
            "Acronyms",
            await cls._static_request_async(
                "get",
                "/company/acronyms",
                user_id,
                company_id=company_id,
            ),
        )
