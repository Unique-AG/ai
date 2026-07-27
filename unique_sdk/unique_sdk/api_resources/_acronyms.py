from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._util import classproperty

if TYPE_CHECKING:
    from unique_sdk._client import _BaseClient


class Acronyms(APIResource["Acronyms"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["company.acronyms"]:
        return "company.acronyms"

    Acronyms: list[list[float]]

    @classmethod
    def get(
        cls, user_id: str, company_id: str, client: "_BaseClient | None" = None
    ) -> "Acronyms":  # pyright: ignore[reportIncompatibleMethodOverride]
        return cast(
            "Acronyms",
            cls._static_request(
                "get",
                "/company/acronyms",
                user_id,
                company_id=company_id,
                client=client,
            ),
        )

    @classmethod
    async def get_async(
        cls, user_id: str, company_id: str, client: "_BaseClient | None" = None
    ) -> "Acronyms":
        return cast(
            "Acronyms",
            await cls._static_request_async(
                "get",
                "/company/acronyms",
                user_id,
                company_id=company_id,
                client=client,
            ),
        )
