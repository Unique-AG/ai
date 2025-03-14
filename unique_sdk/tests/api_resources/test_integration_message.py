from typing import List, cast

import pytest

from unique_sdk.api_resources._message import Message


@pytest.mark.integration
class TestMessage:
    @pytest.mark.run(number="1")
    def test_create_message(self, event):
        """Test creating message synchronously in sandbox."""
        references = cast(
            List[Message.Reference],
            [
                {
                    "name": "Test Doc",
                    "url": "https://example.com/doc",
                    "sequenceNumber": 1,
                    "sourceId": "source1",
                    "source": "test-source",
                }
            ],
        )

        response = Message.create(
            user_id=event.user_id,
            company_id=event.company_id,
            chatId=event.chat_id,
            assistantId=event.assistant_id,
            role="ASSISTANT",
            text="Hello, this is a test message",
            references=references,
        )

        assert response.chatId == event.chat_id
        assert response.text == "Hello, this is a test message"
        assert response.role == "ASSISTANT"

    @pytest.mark.asyncio
    @pytest.mark.run(number="1")
    async def test_create_message_async(self, event):
        """Test creating message asynchronously in sandbox."""
        response = await Message.create_async(
            user_id=event.user_id,
            company_id=event.company_id,
            chatId=event.chat_id,
            assistantId=event.assistant_id,
            role="ASSISTANT",
            text="Hello, this is an async test message",
        )

        assert response.chatId == event.chat_id
        assert response.text == "Hello, this is an async test message"
        assert response.role == "ASSISTANT"

    def test_modify_message(self, event):
        """Test modifying message synchronously in sandbox."""
        data = Message.create(
            user_id=event.user_id,
            company_id=event.company_id,
            chatId=event.chat_id,
            assistantId=event.assistant_id,
            role="ASSISTANT",
            text="Hello, this is a test message",
        )

        response = Message.modify(
            user_id=event.user_id,
            company_id=event.company_id,
            id=data.id,
            chatId=event.chat_id,
            text="Updated test message",
        )

        assert response.chatId == event.chat_id
        assert response.text == "Updated test message"
        assert response.id == data.id

    @pytest.mark.asyncio
    async def test_modify_message_async(self, event):
        """Test modifying message asynchronously in sandbox."""

        data = Message.create(
            user_id=event.user_id,
            company_id=event.company_id,
            chatId=event.chat_id,
            assistantId=event.assistant_id,
            role="ASSISTANT",
            text="Hello, this is a test message",
        )
        response = await Message.modify_async(
            user_id=event.user_id,
            company_id=event.company_id,
            id=data.id,
            chatId=event.chat_id,
            text="Updated async test message",
        )

        assert response.chatId == event.chat_id
        assert response.text == "Updated async test message"
        assert response.id == data.id

    def test_list_messages(self, event):
        """Test listing messages synchronously in sandbox."""
        response = Message.list(
            user_id=event.user_id, company_id=event.company_id, chatId=event.chat_id
        )

        assert isinstance(response.data, list)
        for data in response.data:
            assert data.chatId == event.chat_id

    @pytest.mark.asyncio
    async def test_list_messages_async(self, event):
        """Test listing messages asynchronously in sandbox."""
        response = await Message.list_async(
            user_id=event.user_id, company_id=event.company_id, chatId=event.chat_id
        )

        assert isinstance(response.data, list)
        for data in response.data:
            assert data.chatId == event.chat_id

    def test_retrieve_message(self, event):
        """Test retrieving message synchronously in sandbox."""
        response = Message.retrieve(
            user_id=event.user_id,
            company_id=event.company_id,
            id="msg_zfswj013ouzylrytmugem11t",
            chatId=event.chat_id,
        )

        assert response.id == "msg_zfswj013ouzylrytmugem11t"
        assert response.chatId == event.chat_id

    # @pytest.mark.asyncio
    # async def test_retrieve_message_async(self, event):
    #     """Test retrieving message asynchronously in sandbox."""
    #     response = await Message.retrieve_async(
    #         user_id=event.user_id,
    #         company_id=event.company_id,
    #         id="msg_vlvhmqwnqwn06f758osna5gg",
    #         chatId=event.chat_id,
    #     )

    #     # assert isinstance(response, Message)
    #     assert response.id == "msg_vlvhmqwnqwn06f758osna5gg"
    #     assert response.chatId == event.chat_id

    def test_delete_message(self, event):
        """Test deleting message synchronously in sandbox."""
        data = Message.create(
            user_id=event.user_id,
            company_id=event.company_id,
            chatId=event.chat_id,
            assistantId=event.assistant_id,
            role="ASSISTANT",
            text="Hello, this is a test message",
        )
        response = Message.delete(
            id=data.id,
            user_id=event.user_id,
            company_id=event.company_id,
            chatId=event.chat_id,
        )

        assert response.id == data.id

    # @pytest.mark.asyncio
    # async def test_delete_message_async(self, event):
    #     """Test deleting message asynchronously in sandbox."""
    #     data = Message.create(
    #         user_id=event.user_id,
    #         company_id=event.company_id,
    #         chatId=event.chat_id,
    #         assistantId=event.assistant_id,
    #         role="ASSISTANT",
    #         text="Hello, this is a test message",
    #     )
    #     message = Message(user_id=event.user_id, company_id=event.company_id, id=data.id)
    #     response = await message.delete_async(
    #         user_id=event.user_id, company_id=event.company_id, chatId=event.chat_id
    #     )
    #     assert response.id == data.id
