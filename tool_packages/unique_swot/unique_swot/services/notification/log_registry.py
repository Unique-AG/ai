from typing import Self

from pydantic import BaseModel
from unique_toolkit import ChatService
from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.content.schemas import ContentReference


class MessageLogRegistryItem(BaseModel):
    title: str
    description: list[str]
    sources: list[ContentReference]
    message_log_id: str
    order: int

    @classmethod
    async def create(
        cls,
        *,
        chat_service: ChatService,
        order: int,
        message_id: str,
        title: str,
        description: str,
        sources: list[ContentReference] = [],
    ) -> Self:
        text = f"**{title}**\n - {description}"

        message_log = await chat_service.create_message_log_async(
            message_id=message_id,
            order=order,
            text=text,
            status=MessageLogStatus.RUNNING,
            details=MessageLogDetails(data=[]),
            uncited_references=MessageLogUncitedReferences(data=sources),
            references=sources,
        )

        assert message_log.message_log_id is not None

        return cls(
            title=title,
            description=[description],
            sources=sources,
            message_log_id=message_log.message_log_id,
            order=order,
        )

    async def update(
        self,
        chat_service: ChatService,
        *,
        description: str,
        sources: list[ContentReference],
    ) -> Self:
        self.description.append(description)
        text = f"**{self.title}**\n - {'\n - '.join(self.description)}"
        self.sources.extend(sources)
        await chat_service.update_message_log_async(
            message_log_id=self.message_log_id,
            text=text,
            order=self.order,
            status=MessageLogStatus.RUNNING,
            details=MessageLogDetails(data=[]),
            uncited_references=MessageLogUncitedReferences(data=self.sources),
            references=sources,
        )
        return self


class LogRegistry:
    def __init__(self):
        self._log_registry: dict[str, MessageLogRegistryItem] = {}

    async def add(
        self,
        chat_service: ChatService,
        message_id: str,
        title: str,
        description: str = "",
        sources: list[ContentReference] = [],
    ):
        if title not in self._log_registry:
            self._log_registry[title] = await MessageLogRegistryItem.create(
                chat_service=chat_service,
                order=len(self._log_registry) + 99,
                message_id=message_id,
                title=title,
                description=description,
                sources=sources,
            )
        else:
            await self._log_registry[title].update(
                chat_service=chat_service,
                description=description,
                sources=sources,
            )
