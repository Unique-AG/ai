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
    progress: int
    completed: bool

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
        progress: int = 0,
        completed: bool = False,
    ) -> Self:
        text = f"**{title}** _{progress}%_\n - {description}"

        status = (
            MessageLogStatus.RUNNING if not completed else MessageLogStatus.COMPLETED
        )

        message_log = await chat_service.create_message_log_async(
            message_id=message_id,
            order=order,
            text=text,
            status=status,
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
            progress=progress,
            completed=False,
        )

    async def update(
        self,
        chat_service: ChatService,
        *,
        description: str,
        sources: list[ContentReference],
        progress: int | None = None,
        completed: bool = False,
    ) -> Self:
        self.description.append(description)
        if progress is not None:
            self.progress = progress
        text = (
            f"**{self.title}** _{self.progress}%_\n - {'\n - '.join(self.description)}"
        )
        status = (
            MessageLogStatus.RUNNING if not completed else MessageLogStatus.COMPLETED
        )
        self.sources.extend(sources)
        await chat_service.update_message_log_async(
            message_log_id=self.message_log_id,
            text=text,
            order=self.order,
            status=status,
            details=MessageLogDetails(data=[]),
            uncited_references=MessageLogUncitedReferences(data=self.sources),
            references=sources,
        )
        return self


class LogRegistry:
    def __init__(self):
        self._log_registry: dict[str, MessageLogRegistryItem] = {}
        self._total_number_of_references: int = 0

    async def add(
        self,
        chat_service: ChatService,
        message_id: str,
        title: str,
        description: str = "",
        sources: list[ContentReference] = [],
        progress: int | None = None,
        completed: bool = False,
    ):
        if sources:
            for index, source in enumerate(sources):
                source.sequence_number = index + self._total_number_of_references

        if title not in self._log_registry:
            if progress is None:
                progress = 0
            self._log_registry[title] = await MessageLogRegistryItem.create(
                chat_service=chat_service,
                order=len(self._log_registry) + 99,
                message_id=message_id,
                title=title,
                description=description,
                sources=sources,
                progress=progress,
                completed=completed,
            )
        else:
            await self._log_registry[title].update(
                chat_service=chat_service,
                description=description,
                sources=sources,
                progress=progress,
                completed=completed,
            )
        self._total_number_of_references += len(sources)
