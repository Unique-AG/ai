import json

from unique_sdk.api_resources._short_term_memory import (
    ShortTermMemory as ShortTermMemoryAPI,
)

from .schemas import ShortTermMemory


class ShortTermMemoryService:
    def __init__(
        self, user_id: str, company_id: str, chat_id: str | None, message_id: str | None
    ):
        assert chat_id or message_id, "Either chat_id or message_id must be provided"
        self.user_id = user_id
        self.company_id = company_id
        self.chat_id = chat_id
        self.message_id = message_id

    async def get(self, key: str) -> ShortTermMemory:
        stm = await ShortTermMemoryAPI.find_latest_async(
            user_id=self.user_id,
            company_id=self.company_id,
            memoryName=key,
            chatId=self.chat_id,
            messageId=self.message_id,
        )

        return ShortTermMemory(**stm)

    async def set(self, key: str, value: str | dict):
        if isinstance(value, dict):
            value = json.dumps(value)
        stm = await ShortTermMemoryAPI.create_async(
            user_id=self.user_id,
            company_id=self.company_id,
            memoryName=key,
            chatId=self.chat_id,
            messageId=self.message_id,
            data=value,
        )
        return ShortTermMemory(**stm)
