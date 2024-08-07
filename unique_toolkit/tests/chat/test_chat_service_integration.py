import pytest

from unique_toolkit.app.schemas import Event
from unique_toolkit.chat.service import ChatMessage, ChatMessageRole, ChatService
from unique_toolkit.content.schemas import ContentReference


@pytest.mark.usefixtures("event")
class TestChatServiceIntegration:
    @pytest.fixture(autouse=True)
    def setup(self, event: Event):
        self.event = event
        self.service = ChatService(self.event)

    def test_create_and_modify_assistant_message(self):
        new_message = self.service.create_assistant_message(
            content="Hello, this is a test message.", references=[], debug_info={}
        )
        assert isinstance(new_message, ChatMessage)
        assert new_message.content == "Hello, this is a test message."
        assert new_message.role == ChatMessageRole.ASSISTANT

        modified_message = self.service.modify_assistant_message(
            content="This message has been modified.", message_id=new_message.id
        )
        assert isinstance(modified_message, ChatMessage)
        assert modified_message.content == "This message has been modified."
        assert modified_message.role == ChatMessageRole.ASSISTANT

    def test_get_full_and_selected_history(self):
        self.service.create_assistant_message("Message 1")
        self.service.create_assistant_message("Message 2")

        full_history, selected_history = self.service.get_full_and_selected_history(
            token_limit=1000, percent_of_max_tokens=0.8, max_messages=10
        )

        assert isinstance(selected_history, list)
        assert isinstance(full_history, list)
        assert len(full_history) >= len(selected_history)
        assert all(
            isinstance(msg, ChatMessage) for msg in selected_history + full_history
        )

    def test_create_message_with_references(self):
        references = [
            ContentReference(
                id="doc123",
                message_id="message123",
                name="Document 1",
                sequence_number=1,
                source_id="source123",
                source="source",
                url="http://example.com",
            )
        ]
        message = self.service.create_assistant_message(
            content="This message has a reference.", references=references
        )
        assert isinstance(message, ChatMessage)
        assert message.content == "This message has a reference."

    def test_modify_message_with_debug_info(self):
        new_message = self.service.create_assistant_message("Original message")

        debug_info = {"processing_time": 0.5, "tokens_used": 10}
        modified_message = self.service.modify_assistant_message(
            content="Modified with debug info",
            message_id=new_message.id,
            debug_info=debug_info,
        )
        assert isinstance(modified_message, ChatMessage)
        assert modified_message.content == "Modified with debug info"

        assert hasattr(modified_message, "debug_info")
        assert modified_message.debug_info == debug_info

    def test_get_full_history(self):
        self.service.create_assistant_message("Message 1")
        self.service.create_assistant_message("Message 2")

        full_history = self.service.get_full_history()

        assert isinstance(full_history, list)
        assert all(isinstance(msg, ChatMessage) for msg in full_history)

    @pytest.mark.asyncio
    async def test_get_full_history_async(self):
        self.service.create_assistant_message("Message 1")
        self.service.create_assistant_message("Message 2")

        full_history = await self.service.get_full_history_async()

        assert isinstance(full_history, list)
        assert all(isinstance(msg, ChatMessage) for msg in full_history)

    @pytest.mark.asyncio
    async def test_create_and_modify_assistant_message_async(self):
        new_message = await self.service.create_assistant_message_async(
            content="Hello, this is a test message.", references=[], debug_info={}
        )
        assert isinstance(new_message, ChatMessage)
        assert new_message.content == "Hello, this is a test message."
        assert new_message.role == ChatMessageRole.ASSISTANT

        modified_message = await self.service.modify_assistant_message_async(
            content="This message has been modified.", message_id=new_message.id
        )
        assert isinstance(modified_message, ChatMessage)
        assert modified_message.content == "This message has been modified."
        assert modified_message.role == ChatMessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_get_full_and_selected_history_async(self):
        await self.service.create_assistant_message_async("Message 1")
        await self.service.create_assistant_message_async("Message 2")

        (
            full_history,
            selected_history,
        ) = await self.service.get_full_and_selected_history_async(
            token_limit=1000, percent_of_max_tokens=0.8, max_messages=10
        )

        assert isinstance(selected_history, list)
        assert isinstance(full_history, list)
        assert len(full_history) >= len(selected_history)
        assert all(
            isinstance(msg, ChatMessage) for msg in selected_history + full_history
        )

    @pytest.mark.asyncio
    async def test_create_message_with_references_async(self):
        references = [
            ContentReference(
                id="doc123",
                message_id="message123",
                name="Document 1",
                sequence_number=1,
                source_id="source123",
                source="source",
                url="http://example.com",
            )
        ]
        message = await self.service.create_assistant_message_async(
            content="This message has a reference.", references=references
        )
        assert isinstance(message, ChatMessage)
        assert message.content == "This message has a reference."

    @pytest.mark.asyncio
    async def test_modify_message_with_debug_info_async(self):
        new_message = await self.service.create_assistant_message_async(
            "Original message"
        )

        debug_info = {"processing_time": 0.5, "tokens_used": 10}
        modified_message = await self.service.modify_assistant_message_async(
            content="Modified with debug info",
            message_id=new_message.id,
            debug_info=debug_info,
        )
        assert isinstance(modified_message, ChatMessage)
        assert modified_message.content == "Modified with debug info"

        assert hasattr(modified_message, "debug_info")
        assert modified_message.debug_info == debug_info
