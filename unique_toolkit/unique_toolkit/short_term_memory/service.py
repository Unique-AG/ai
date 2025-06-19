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
        self._event = event
        if event:
            self._company_id: str = event.company_id
            self._user_id: str = event.user_id
            if isinstance(event, (ChatEvent, Event)):
                self._chat_id = event.payload.chat_id
                self._message_id = event.payload.user_message.id
        else:
            [company_id, user_id] = validate_required_values([company_id, user_id])
            assert (
                chat_id or message_id
            ), "Either chat_id or message_id must be provided"

            self._company_id: str = company_id
            self._user_id: str = user_id
            self._chat_id: str | None = chat_id
            self._message_id: str | None = message_id

    @property
    @deprecated(
        "The event property is deprecated and will be removed in a future version."
    )
    def event(self) -> Event | BaseEvent | None:
        """
        Get the event object (deprecated).

        Returns:
            Event | BaseEvent | None: The event object.
        """
        return self._event

    @property
    @deprecated(
        "The company_id property is deprecated and will be removed in a future version."
    )
    def company_id(self) -> str | None:
        """
        Get the company identifier (deprecated).

        Returns:
            str | None: The company identifier.
        """
        return self._company_id

    @company_id.setter
    @deprecated(
        "The company_id setter is deprecated and will be removed in a future version."
    )
    def company_id(self, value: str) -> None:
        """
        Set the company identifier (deprecated).

        Args:
            value (str | None): The company identifier.
        """
        self._company_id = value

    @property
    @deprecated(
        "The user_id property is deprecated and will be removed in a future version."
    )
    def user_id(self) -> str | None:
        """
        Get the user identifier (deprecated).

        Returns:
            str | None: The user identifier.
        """
        return self._user_id

    @user_id.setter
    @deprecated(
        "The user_id setter is deprecated and will be removed in a future version."
    )
    def user_id(self, value: str) -> None:
        """
        Set the user identifier (deprecated).

        Args:
            value (str | None): The user identifier.
        """
        self._user_id = value

    @property
    @deprecated(
        "The chat_id property is deprecated and will be removed in a future version."
    )
    def chat_id(self) -> str | None:
        """
        Get the chat identifier (deprecated).

        Returns:
            str | None: The chat identifier.
        """
        return self._chat_id

    @chat_id.setter
    @deprecated(
        "The chat_id setter is deprecated and will be removed in a future version."
    )
    def chat_id(self, value: str | None) -> None:
        """
        Set the chat identifier (deprecated).

        Args:
            value (str | None): The chat identifier.
        """
        self._chat_id = value

    @property
    @deprecated(
        "The message_id property is deprecated and will be removed in a future version."
    )
    def message_id(self) -> str | None:
        """
        Get the message identifier (deprecated).

        Returns:
            str | None: The message identifier.
        """
        return self._message_id

    @message_id.setter
    @deprecated(
        "The message_id setter is deprecated and will be removed in a future version."
    )
    def message_id(self, value: str | None) -> None:
        """
        Set the message identifier (deprecated).

        Args:
            value (str | None): The message identifier.
        """
        self._message_id = value

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
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            chat_id=self._chat_id,
            message_id=self._message_id,
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
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            chat_id=self._chat_id,
            message_id=self._message_id,
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
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            value=value,
            chat_id=self._chat_id,
            message_id=self._message_id,
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
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            value=value,
            chat_id=self._chat_id,
            message_id=self._message_id,
        )

    @deprecated("Use create_memory_async instead")
    async def set(self, key: str, value: str | dict):
        return await create_memory_async(
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            value=value,
            chat_id=self._chat_id,
            message_id=self._message_id,
        )

    @deprecated("Use find_latest_memory_async instead")
    async def get(self, key: str) -> ShortTermMemory:
        return await find_latest_memory_async(
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            chat_id=self._chat_id,
            message_id=self._message_id,
        )
