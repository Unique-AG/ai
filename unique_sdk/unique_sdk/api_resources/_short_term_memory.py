from typing import Literal, cast

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions
from unique_sdk._util import classproperty


class ShortTermMemory(APIResource["ShortTermMemory"]):
    @classproperty
    def OBJECT_NAME(cls) -> Literal["ShortTermMemory"]:
        return "ShortTermMemory"

    class CreateParams(RequestOptions):
        memoryName: str
        chatId: str | None
        messageId: NotRequired[str | None]
        data: str | None

    class FindParams(RequestOptions):
        memoryName: str
        chatId: str | None
        messageId: NotRequired[str | None]

    id: str
    memoryName: str
    chatId: str | None
    messageId: str | None
    data: str | None

    @classmethod
    def create(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["ShortTermMemory.CreateParams"],
    ) -> "ShortTermMemory":
        """
        Create Short Term Memory
        """
        return cast(
            "ShortTermMemory",
            cls._static_request(
                "post",
                "/short-term-memory",
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
        **params: Unpack["ShortTermMemory.CreateParams"],
    ) -> "ShortTermMemory":
        """
        Create Short Term Memory
        """
        return cast(
            "ShortTermMemory",
            await cls._static_request_async(
                "post",
                "/short-term-memory",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    def find_latest(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["ShortTermMemory.FindParams"],
    ) -> "ShortTermMemory":
        """
        Find latest Short Term Memory
        """
        return cast(
            "ShortTermMemory",
            cls._static_request(
                "post",
                "/short-term-memory/find-latest",
                user_id,
                company_id,
                params=params,
            ),
        )

    @classmethod
    async def find_latest_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["ShortTermMemory.FindParams"],
    ) -> "ShortTermMemory":
        """
        Find latest Short Term Memory
        """
        return cast(
            "ShortTermMemory",
            await cls._static_request_async(
                "post",
                "/short-term-memory/find-latest",
                user_id,
                company_id,
                params=params,
            ),
        )
