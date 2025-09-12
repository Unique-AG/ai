"""
Messages API resource for the Unique SDK v2.
"""

from unique_client.core import APIResource
from unique_client.unique_client.api_resources.api_dtos import (
    DeletedObjectDto,
    ListObjectDto,
    PublicCreateMessageDto,
    PublicMessageDto,
    PublicUpdateMessageDto,
)


class Messages(APIResource):
    """
    Messages API resource for managing message operations.

    This class provides both sync and async methods for creating, retrieving, updating,
    and deleting messages in chats.

    All methods use the intrinsic RequestContextProtocol for automatic header and URL handling.
    """

    OBJECT_NAME = "messages"

    # Synchronous methods
    # ==================

    def list(self, chat_id: str) -> ListObjectDto:
        """List all messages for a chat using the intrinsic RequestContextProtocol."""
        return self._request(
            "get",
            "/messages",
            model_class=ListObjectDto,
            params={"chatId": chat_id},
        )

    def create(self, params: PublicCreateMessageDto) -> PublicMessageDto:
        """Create a new message using the intrinsic RequestContextProtocol."""
        return self._request(
            "post",
            "/messages",
            model_class=PublicMessageDto,
            params=params,
        )

    def retrieve(self, message_id: str, chat_id: str) -> PublicMessageDto:
        """Retrieve a specific message using the intrinsic RequestContextProtocol."""
        return self._request(
            "get",
            f"/messages/{message_id}",
            model_class=PublicMessageDto,
            params={"chatId": chat_id},
        )

    def update(
        self, message_id: str, params: PublicUpdateMessageDto
    ) -> PublicMessageDto:
        """Update a message using the intrinsic RequestContextProtocol."""
        return self._request(
            "patch",
            f"/messages/{message_id}",
            model_class=PublicMessageDto,
            params=params,
        )

    def delete(self, message_id: str, chat_id: str) -> DeletedObjectDto:
        """Delete a message using the intrinsic RequestContextProtocol."""
        return self._request(
            "delete",
            f"/messages/{message_id}",
            model_class=DeletedObjectDto,
            params={"chatId": chat_id},
        )

    # Asynchronous methods
    # ===================

    async def list_async(self, chat_id: str) -> ListObjectDto:
        """List all messages for a chat asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "get",
            "/messages",
            model_class=ListObjectDto,
            params={"chatId": chat_id},
        )

    async def create_async(self, params: PublicCreateMessageDto) -> PublicMessageDto:
        """Create a new message asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "post",
            "/messages",
            model_class=PublicMessageDto,
            params=params,
        )

    async def retrieve_async(self, message_id: str, chat_id: str) -> PublicMessageDto:
        """Retrieve a specific message asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "get",
            f"/messages/{message_id}",
            model_class=PublicMessageDto,
            params={"chatId": chat_id},
        )

    async def update_async(
        self, message_id: str, params: PublicUpdateMessageDto
    ) -> PublicMessageDto:
        """Update a message asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "patch",
            f"/messages/{message_id}",
            model_class=PublicMessageDto,
            params=params,
        )

    async def delete_async(self, message_id: str, chat_id: str) -> DeletedObjectDto:
        """Delete a message asynchronously using the intrinsic RequestContextProtocol."""
        return await self._request_async(
            "delete",
            f"/messages/{message_id}",
            model_class=DeletedObjectDto,
            params={"chatId": chat_id},
        )
