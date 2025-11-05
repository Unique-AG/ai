from typing import ClassVar, Literal, Optional, cast

from typing_extensions import NotRequired, Unpack

from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions


class ShortTermMemory(APIResource["ShortTermMemory"]):
    OBJECT_NAME: ClassVar[Literal["ShortTermMemory"]] = "ShortTermMemory"

    class CreateParams(RequestOptions):
        memoryName: str
        chatId: Optional[str]
        messageId: NotRequired[Optional[str]]
        data: Optional[str]

    class FindParams(RequestOptions):
        memoryName: str
        chatId: Optional[str]
        messageId: NotRequired[Optional[str]]

    id: str
    chatId: Optional[str]
    messageId: Optional[str]
    data: str

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
