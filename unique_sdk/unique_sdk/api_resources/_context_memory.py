from typing import Literal, Unpack, cast

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class ContextMemory(APIResource["ContextMemory"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["context-memory"]:
        return "context-memory"

    RESOURCE_URL = "/context-memory"

    class UpdateParams(RequestOptions):
        document: str

    scopeId: str
    contentId: str
    document: str
    updatedAt: str
    object: Literal["context-memory"]

    @classmethod
    def retrieve(cls, user_id: str, company_id: str) -> "ContextMemory":
        return cast(
            "ContextMemory",
            cls._static_request("get", cls.RESOURCE_URL, user_id, company_id),
        )

    @classmethod
    async def retrieve_async(cls, user_id: str, company_id: str) -> "ContextMemory":
        return cast(
            "ContextMemory",
            await cls._static_request_async(
                "get", cls.RESOURCE_URL, user_id, company_id
            ),
        )

    @classmethod
    def modify(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["ContextMemory.UpdateParams"],
    ) -> "ContextMemory":
        return cast(
            "ContextMemory",
            cls._static_request(
                "patch",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def modify_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["ContextMemory.UpdateParams"],
    ) -> "ContextMemory":
        return cast(
            "ContextMemory",
            await cls._static_request_async(
                "patch",
                cls.RESOURCE_URL,
                user_id,
                company_id,
                params=params,
            ),
        )
