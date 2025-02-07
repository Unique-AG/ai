from typing_extensions import deprecated

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app import Event
from unique_toolkit.app.schemas import BaseEvent, ChatEvent
from unique_toolkit.short_term_memory.functions import (
    create_memory,
    create_memory_async,
    find_latest_memory,
    find_latest_memory_async,
)

from .schemas import ShortTermMemory


class ShortTermMemoryService:
    """
    Provides methods to manage short term memory.

    Attributes:
        event (Event | BaseEvent | None): The event object.
        user_id (str | None): The user ID.
        company_id (str | None): The company ID.
        chat_id (str | None): The chat ID.
        message_id (str | None): The message ID.
    """

    def __init__(
        self,
        event: Event | BaseEvent | None = None,
        user_id: str | None = None,
        company_id: str | None = None,
        chat_id: str | None = None,
        message_id: str | None = None,
    ):
        self.event = event
        if event:
            self.company_id = event.company_id
            self.user_id = event.user_id
            if isinstance(event, (ChatEvent, Event)):
                self.chat_id = event.payload.chat_id
                self.message_id = event.payload.user_message.id
        else:
            [company_id, user_id] = validate_required_values([company_id, user_id])
            assert (
                chat_id or message_id
            ), "Either chat_id or message_id must be provided"
            self.company_id = company_id
            self.user_id = user_id
            self.chat_id = chat_id
            self.message_id = message_id

    @classmethod
    @deprecated("Instantiate class directly from event")
    def from_chat_event(cls, chat_event: Event) -> "ShortTermMemoryService":
        return cls(
            user_id=chat_event.user_id,
            company_id=chat_event.company_id,
            chat_id=chat_event.payload.chat_id,
            message_id=chat_event.payload.user_message.id,
        )

    async def find_latest_memory_async(self, key: str) -> ShortTermMemory:
        """
        Find the latest short term memory.

        Args:
            key (str): The key.

        Returns:
            ShortTermMemory: The latest short term memory.

        Raises:
            Exception: If an error occurs.
        """

        return await find_latest_memory_async(
            user_id=self.user_id,
            company_id=self.company_id,
            key=key,
            chat_id=self.chat_id,
            message_id=self.message_id,
        )

    def find_latest_memory(self, key: str) -> ShortTermMemory:
        """
        Find the latest short term memory.

        Args:
            key (str): The key.

        Returns:
            ShortTermMemory: The latest short term memory.

        Raises:
            Exception: If an error occurs.
        """

        return find_latest_memory(
            user_id=self.user_id,
            company_id=self.company_id,
            key=key,
            chat_id=self.chat_id,
            message_id=self.message_id,
        )

    async def create_memory_async(self, key: str, value: str | dict):
        """
        Create a short term memory.

        Args:
            key (str): The key.
            value (str | dict): The value.

        Returns:
            ShortTermMemory: The created short term memory.

        Raises:
            Exception: If an error occurs.
        """

        return await create_memory_async(
            user_id=self.user_id,
            company_id=self.company_id,
            key=key,
            value=value,
        )

    def create_memory(self, key: str, value: str | dict):
        """
        Create a short term memory.

        Args:
            key (str): The key.
            value (str | dict): The value.
        Returns:
            ShortTermMemory: The created short term memory.

        Raises:
            Exception: If an error occurs.
        """

        return create_memory(
            user_id=self.user_id,
            company_id=self.company_id,
            key=key,
            value=value,
            chat_id=self.chat_id,
            message_id=self.message_id,
        )

    @deprecated("Use create_memory_async instead")
    async def set(self, key: str, value: str | dict):
        return await create_memory_async(
            user_id=self.user_id,
            company_id=self.company_id,
            key=key,
            value=value,
            chat_id=self.chat_id,
            message_id=self.message_id,
        )

    @deprecated("Use find_latest_memory_async instead")
    async def get(self, key: str) -> ShortTermMemory:
        return await find_latest_memory_async(
            user_id=self.user_id,
            company_id=self.company_id,
            key=key,
            chat_id=self.chat_id,
            message_id=self.message_id,
        )
