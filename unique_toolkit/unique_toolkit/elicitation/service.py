from typing import Any, Literal

from unique_toolkit._common.validate_required_values import validate_required_values
from unique_toolkit.app.schemas import BaseEvent, ChatEvent, Event
from unique_toolkit.elicitation.functions import (
    create_elicitation,
    create_elicitation_async,
    get_elicitation,
    get_elicitation_async,
    get_pending_elicitations,
    get_pending_elicitations_async,
    respond_to_elicitation,
    respond_to_elicitation_async,
)
from unique_toolkit.elicitation.schemas import (
    Elicitation,
    ElicitationList,
    ElicitationResponseResult,
)


class ElicitationService:
    """
    Provides all functionalities to manage elicitation requests.
    """

    def __init__(
        self,
        user_id: str,
        company_id: str,
        chat_id: str | None = None,
        message_id: str | None = None,
        mcp_server_id: str | None = None,
    ):
        """
        Initialize the ElicitationService.

        Args:
            user_id (str): The user ID.
            company_id (str): The company ID.
            chat_id (str, optional): The chat ID if elicitation is associated with a chat.
            message_id (str, optional): The message ID if elicitation is associated with a message.
            mcp_server_id (str, optional): The MCP server ID if elicitation is from MCP.
        """
        [company_id, user_id] = validate_required_values([company_id, user_id])
        self._company_id = company_id
        self._user_id = user_id
        self._chat_id = chat_id
        self._message_id = message_id
        self._mcp_server_id = mcp_server_id

    @classmethod
    def from_event(cls, event: BaseEvent):
        """
        Create an ElicitationService from an event.

        Args:
            event (BaseEvent): The event object.

        Returns:
            ElicitationService: The ElicitationService instance.
        """
        chat_id = None
        message_id = None

        if isinstance(event, (ChatEvent, Event)):
            chat_id = event.payload.chat_id
            # Use user_message.id as the message_id
            if hasattr(event.payload, "user_message") and event.payload.user_message:
                message_id = event.payload.user_message.id

        return cls(
            company_id=event.company_id,
            user_id=event.user_id,
            chat_id=chat_id,
            message_id=message_id,
        )

    @property
    def user_id(self) -> str:
        """Get the user ID."""
        return self._user_id

    @property
    def company_id(self) -> str:
        """Get the company ID."""
        return self._company_id

    @property
    def chat_id(self) -> str | None:
        """Get the chat ID."""
        return self._chat_id

    @property
    def message_id(self) -> str | None:
        """Get the message ID."""
        return self._message_id

    @property
    def mcp_server_id(self) -> str | None:
        """Get the MCP server ID."""
        return self._mcp_server_id

    # Create Methods
    ############################################################################

    def create(
        self,
        mode: Literal["FORM", "URL"],
        message: str,
        tool_name: str,
        json_schema: dict[str, Any] | None = None,
        url: str | None = None,
        external_elicitation_id: str | None = None,
        chat_id: str | None = None,
        message_id: str | None = None,
        expires_in_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Elicitation:
        """
        Create an elicitation request synchronously.

        Args:
            mode (Literal["FORM", "URL"]): The elicitation mode.
            message (str): The message to display to the user.
            tool_name (str): The name of the tool requesting elicitation.
            json_schema (dict[str, Any], optional): JSON schema for FORM mode.
            url (str, optional): URL for URL mode.
            external_elicitation_id (str, optional): External elicitation ID for tracking.
            chat_id (str, optional): The chat ID. If not provided, uses the service's chat_id.
            message_id (str, optional): The message ID. If not provided, uses the service's message_id.
            expires_in_seconds (int, optional): Expiration time in seconds.
            metadata (dict[str, Any], optional): Additional metadata.

        Returns:
            Elicitation: The created elicitation.

        Raises:
            Exception: If the creation fails.
        """
        return create_elicitation(
            user_id=self._user_id,
            company_id=self._company_id,
            mode=mode,
            message=message,
            tool_name=tool_name,
            json_schema=json_schema,
            url=url,
            external_elicitation_id=external_elicitation_id,
            chat_id=chat_id or self._chat_id,
            message_id=message_id or self._message_id,
            expires_in_seconds=expires_in_seconds,
            metadata=metadata,
        )

    async def create_async(
        self,
        mode: Literal["FORM", "URL"],
        message: str,
        tool_name: str,
        json_schema: dict[str, Any] | None = None,
        url: str | None = None,
        external_elicitation_id: str | None = None,
        chat_id: str | None = None,
        message_id: str | None = None,
        expires_in_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Elicitation:
        """
        Create an elicitation request asynchronously.

        Args:
            mode (Literal["FORM", "URL"]): The elicitation mode.
            message (str): The message to display to the user.
            tool_name (str): The name of the tool requesting elicitation.
            json_schema (dict[str, Any], optional): JSON schema for FORM mode.
            url (str, optional): URL for URL mode.
            external_elicitation_id (str, optional): External elicitation ID for tracking.
            chat_id (str, optional): The chat ID. If not provided, uses the service's chat_id.
            message_id (str, optional): The message ID. If not provided, uses the service's message_id.
            expires_in_seconds (int, optional): Expiration time in seconds.
            metadata (dict[str, Any], optional): Additional metadata.

        Returns:
            Elicitation: The created elicitation.

        Raises:
            Exception: If the creation fails.
        """
        return await create_elicitation_async(
            user_id=self._user_id,
            company_id=self._company_id,
            mode=mode,
            message=message,
            tool_name=tool_name,
            json_schema=json_schema,
            url=url,
            external_elicitation_id=external_elicitation_id,
            chat_id=chat_id or self._chat_id,
            message_id=message_id or self._message_id,
            expires_in_seconds=expires_in_seconds,
            metadata=metadata,
        )

    # Get Methods
    ############################################################################

    def get(self, elicitation_id: str) -> Elicitation:
        """
        Get an elicitation request by ID synchronously.

        Args:
            elicitation_id (str): The elicitation ID.

        Returns:
            Elicitation: The elicitation.

        Raises:
            Exception: If the request fails.
        """
        return get_elicitation(
            user_id=self._user_id,
            company_id=self._company_id,
            elicitation_id=elicitation_id,
        )

    async def get_async(self, elicitation_id: str) -> Elicitation:
        """
        Get an elicitation request by ID asynchronously.

        Args:
            elicitation_id (str): The elicitation ID.

        Returns:
            Elicitation: The elicitation.

        Raises:
            Exception: If the request fails.
        """
        return await get_elicitation_async(
            user_id=self._user_id,
            company_id=self._company_id,
            elicitation_id=elicitation_id,
        )

    # List Pending Methods
    ############################################################################

    def list_pending(self) -> ElicitationList:
        """
        Get all pending elicitation requests synchronously.

        Returns:
            ElicitationList: The list of pending elicitations.

        Raises:
            Exception: If the request fails.
        """
        return get_pending_elicitations(
            user_id=self._user_id,
            company_id=self._company_id,
        )

    async def list_pending_async(self) -> ElicitationList:
        """
        Get all pending elicitation requests asynchronously.

        Returns:
            ElicitationList: The list of pending elicitations.

        Raises:
            Exception: If the request fails.
        """
        return await get_pending_elicitations_async(
            user_id=self._user_id,
            company_id=self._company_id,
        )

    # Respond Methods
    ############################################################################

    def respond(
        self,
        elicitation_id: str,
        action: Literal["ACCEPT", "DECLINE", "CANCEL"],
        content: dict[str, str | int | bool | list[str]] | None = None,
    ) -> ElicitationResponseResult:
        """
        Respond to an elicitation request synchronously.

        Args:
            elicitation_id (str): The elicitation ID.
            action (Literal["ACCEPT", "DECLINE", "CANCEL"]): The action to take.
            content (dict[str, str | int | bool | list[str]], optional): Response content for ACCEPT action.

        Returns:
            ElicitationResponseResult: The response result.

        Raises:
            Exception: If the response fails.
        """
        return respond_to_elicitation(
            user_id=self._user_id,
            company_id=self._company_id,
            elicitation_id=elicitation_id,
            action=action,
            content=content,
        )

    async def respond_async(
        self,
        elicitation_id: str,
        action: Literal["ACCEPT", "DECLINE", "CANCEL"],
        content: dict[str, str | int | bool | list[str]] | None = None,
    ) -> ElicitationResponseResult:
        """
        Respond to an elicitation request asynchronously.

        Args:
            elicitation_id (str): The elicitation ID.
            action (Literal["ACCEPT", "DECLINE", "CANCEL"]): The action to take.
            content (dict[str, str | int | bool | list[str]], optional): Response content for ACCEPT action.

        Returns:
            ElicitationResponseResult: The response result.

        Raises:
            Exception: If the response fails.
        """
        return await respond_to_elicitation_async(
            user_id=self._user_id,
            company_id=self._company_id,
            elicitation_id=elicitation_id,
            action=action,
            content=content,
        )
