from unittest.mock import patch

import pytest
import unique_sdk
import unique_sdk.utils

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.chat.service import ChatService
from unique_toolkit.chat.state import ChatState
from unique_toolkit.content.schemas import ContentReference


class TestChatServiceUnit:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.chat_state = ChatState(
            user_id="test_user",
            company_id="test_company",
            chat_id="test_chat",
            assistant_id="test_assistant",
        )
        self.service = ChatService(self.chat_state)

    def test_modify_assistant_message(self):
        with patch.object(unique_sdk.Message, "modify", autospec=True) as mock_modify:
            mock_modify.return_value = {
                "id": "test_message",
                "content": "Modified message",
                "role": "assistant",
            }
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

            result = self.service.modify_assistant_message(
                content="Modified message",
                message_id="test_assistant_message",
                references=references,
                debug_info={},
            )

            assert isinstance(result, ChatMessage)
            assert result.content == "Modified message"
            assert result.role == ChatMessageRole.ASSISTANT

            mock_modify.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                id="test_assistant_message",
                chatId="test_chat",
                text="Modified message",
                references=[
                    {
                        "name": "Document 1",
                        "url": "http://example.com",
                        "sequenceNumber": 1,
                        "sourceId": "source123",
                        "source": "source",
                    }
                ],
                debugInfo={},
            )

    def test_get_history(self):
        with patch.object(unique_sdk.Message, "list", autospec=True) as mock_list:
            mock_list.return_value = {
                "object": "list",
                "data": [
                    {"id": "message1", "text": "Message 1", "role": "assistant"},
                    {"id": "message2", "text": "Message 2", "role": "user"},
                    {"id": "message3", "text": "Message 3", "role": "assistant"},
                    {"id": "message4", "text": "Message 4", "role": "user"},
                ],
            }

            full_history, selected_history = self.service.get_full_and_selected_history(
                token_limit=100,
                percent_of_max_tokens=0.8,
                max_messages=1,
            )

            assert len(selected_history) == 1
            assert len(full_history) == 2
            assert all(
                isinstance(msg, ChatMessage) for msg in selected_history + full_history
            )

            mock_list.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                chatId="test_chat",
            )

    def test_create_assistant_message(self):
        with patch.object(unique_sdk.Message, "create", autospec=True) as mock_create:
            mock_create.return_value = {
                "id": "new_message",
                "content": "New assistant message",
                "role": "assistant",
            }

            result = self.service.create_assistant_message(
                content="New assistant message", references=[], debug_info={}
            )

            assert isinstance(result, ChatMessage)
            assert result.content == "New assistant message"
            assert result.role == ChatMessageRole.ASSISTANT

            mock_create.assert_called_once_with(
                user_id="test_user",
                company_id="test_company",
                chatId="test_chat",
                assistantId="test_assistant",
                text="New assistant message",
                role="ASSISTANT",
                references=[],
                debugInfo={},
            )

    def test_error_handling_modify_message(self):
        with patch.object(
            unique_sdk.Message,
            "modify",
            autospec=True,
            side_effect=Exception("API Error"),
        ):
            with pytest.raises(Exception, match="API Error"):
                self.service.modify_assistant_message("Modified message")

    def test_error_handling_get_history(self):
        with patch.object(
            unique_sdk.Message,
            "list",
            side_effect=Exception("History Error"),
        ):
            with pytest.raises(Exception, match="History Error"):
                self.service.get_full_and_selected_history(100, 0.8, 10)

    def test_error_handling_create_message(self):
        with patch.object(
            unique_sdk.Message,
            "create",
            autospec=True,
            side_effect=Exception("Creation Error"),
        ):
            with pytest.raises(Exception, match="Creation Error"):
                self.service.create_assistant_message("New message")
