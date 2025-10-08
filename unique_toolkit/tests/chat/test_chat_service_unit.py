import json
from unittest import mock
from unittest.mock import patch

import pytest
import unique_sdk
import unique_sdk.utils

from tests.test_obj_factory import get_event_obj
from unique_toolkit._common.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.app.schemas import (
    Event,
    EventAssistantMessage,
    EventName,
    EventPayload,
    EventUserMessage,
)
from unique_toolkit.chat.schemas import (
    ChatMessage,
    ChatMessageAssessment,
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
    ChatMessageRole,
)
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
    LanguageModelTool,
    LanguageModelToolParameterProperty,
    LanguageModelToolParameters,
)

mocked_datetime = "2024-08-08 12:00:00.000000"
# Mock tool for testing
mock_tool = LanguageModelTool(
    name="get_weather",
    description="Get the current weather for a location",
    parameters=LanguageModelToolParameters(
        type="object",
        properties={
            "location": LanguageModelToolParameterProperty(
                type="string", description="The city and state, e.g. San Francisco, CA"
            ),
            "unit": LanguageModelToolParameterProperty(
                type="string",
                description="The unit system to use. Either 'celsius' or 'fahrenheit'.",
                enum=["celsius", "fahrenheit"],
            ),
        },
        required=["location"],
    ),
)


@pytest.fixture
def mock_get_datetime_now(mocker):
    return mocker.patch(
        "unique_toolkit._common._time_utils.get_datetime_now",
        return_value=mocked_datetime,
    )


class TestChatServiceUnit:
    @pytest.fixture(autouse=True)
    def setup(self, mock_get_datetime_now):
        self.event = get_event_obj(
            user_id="test_user",
            company_id="test_company",
            chat_id="test_chat",
            assistant_id="test_assistant",
        )
        self.service = ChatService(self.event)
        self.mock_get_datetime_now = mock_get_datetime_now

    @pytest.mark.unit
    @patch.object(unique_sdk.Message, "modify", autospec=True)
    def test_modify_assistant_message(self, mock_modify):
        # Test with update completedAt
        mock_modify.return_value = {
            "id": "test_message",
            "content": "Modified message",
            "role": "assistant",
            "chatId": "chatId123",
            "originalText": "originText",
            "createdAt": mocked_datetime,
            "updatedAt": mocked_datetime,
            "completedAt": mocked_datetime,
        }
        mock_modify.return_value = {
            "id": "test_message",
            "chatId": "chatId123",
            "content": "Modified message",
            "role": "assistant",
        }
        mock_modify.return_value = {
            "id": "test_message",
            "chatId": "chatId123",
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
            set_completed_at=True,
        )
        result = self.service.modify_assistant_message(
            content="Modified message",
            message_id="test_assistant_message",
            references=references,
            debug_info={},
            set_completed_at=True,
        )

        assert isinstance(result, ChatMessage)
        assert result.content == "Modified message"
        assert result.role == ChatMessageRole.ASSISTANT
        assert isinstance(result, ChatMessage)
        assert result.content == "Modified message"
        assert result.role == ChatMessageRole.ASSISTANT

        expected_calls = [
            mock.call(
                user_id="test_user",
                company_id="test_company",
                id="test_assistant_message",
                chatId="test_chat",
                text="Modified message",
                originalText=None,
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
                completedAt=mocked_datetime,
            )
        ]
        mock_modify.assert_has_calls(expected_calls)
        mock_modify.reset_mock()

        # Test without update completedAt
        mock_modify.return_value = {
            "id": "test_message",
            "content": "Modified message",
            "role": "assistant",
            "chatId": "chatId123",
        }

        result = self.service.modify_assistant_message(
            content="Modified message",
            message_id="test_assistant_message",
            references=references,
            debug_info={},
        )

        assert isinstance(result, ChatMessage)
        assert result.content == "Modified message"
        assert result.role == ChatMessageRole.ASSISTANT

        expected_calls = [
            mock.call(
                user_id="test_user",
                company_id="test_company",
                id="test_assistant_message",
                chatId="test_chat",
                text="Modified message",
                originalText=None,
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
                completedAt=None,
            )
        ]
        mock_modify.assert_has_calls(expected_calls)

    @patch.object(unique_sdk.Message, "list", autospec=True)
    def test_get_history(self, mock_list):
        mock_list.return_value = {
            "object": "list",
            "data": [
                {
                    "id": "message1",
                    "text": "Message 1",
                    "role": "assistant",
                    "chatId": "chatId123",
                    "originalText": "originText",
                    "createdAt": mocked_datetime,
                    "updatedAt": mocked_datetime,
                    "completedAt": mocked_datetime,
                },
                {
                    "id": "message2",
                    "text": "Message 2",
                    "role": "user",
                    "chatId": "chatId123",
                    "originalText": "originText",
                    "createdAt": mocked_datetime,
                    "updatedAt": mocked_datetime,
                    "completedAt": mocked_datetime,
                },
                {
                    "id": "message3",
                    "text": "Message 3",
                    "role": "assistant",
                    "chatId": "chatId123",
                    "originalText": "originText",
                    "createdAt": mocked_datetime,
                    "updatedAt": mocked_datetime,
                    "completedAt": mocked_datetime,
                },
                {
                    "id": "message4",
                    "text": "Message 4",
                    "role": "user",
                    "chatId": "chatId123",
                    "originalText": "originText",
                    "createdAt": mocked_datetime,
                    "updatedAt": mocked_datetime,
                    "completedAt": mocked_datetime,
                },
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

    @patch.object(unique_sdk.Message, "create", autospec=True)
    def test_create_assistant_message(self, mock_create):
        # Test with update completedAt
        mock_create.return_value = {
            "content": "New assistant message",
            "role": "assistant",
            "chatId": "chatId123",
        }

        result = self.service.create_assistant_message(
            content="New assistant message",
            references=[],
            debug_info={},
            set_completed_at=True,
        )
        result = self.service.create_assistant_message(
            content="New assistant message",
            references=[],
            debug_info={},
            set_completed_at=True,
        )

        assert isinstance(result, ChatMessage)
        assert result.content == "New assistant message"
        assert result.role == ChatMessageRole.ASSISTANT.value
        assert isinstance(result, ChatMessage)
        assert result.content == "New assistant message"
        assert result.role == ChatMessageRole.ASSISTANT.value

        expected_calls = [
            mock.call(
                user_id="test_user",
                company_id="test_company",
                assistantId="test_assistant",
                role="ASSISTANT",
                chatId="test_chat",
                text="New assistant message",
                originalText="New assistant message",
                references=[],
                debugInfo={},
                completedAt=mocked_datetime,
            )
        ]
        mock_create.assert_has_calls(expected_calls)
        mock_create.reset_mock()

        # Test without update completedAt
        mock_create.return_value = {
            "content": "New assistant message",
            "role": "assistant",
            "chatId": "chatId123",
        }

        result = self.service.create_assistant_message(
            content="New assistant message",
            references=[],
            debug_info={},
        )

        assert isinstance(result, ChatMessage)
        assert result.content == "New assistant message"
        assert result.role == ChatMessageRole.ASSISTANT

        expected_calls = [
            mock.call(
                user_id="test_user",
                company_id="test_company",
                assistantId="test_assistant",
                role="ASSISTANT",
                chatId="test_chat",
                text="New assistant message",
                originalText="New assistant message",
                references=[],
                debugInfo={},
                completedAt=None,
            )
        ]
        mock_create.assert_has_calls(expected_calls)

    @patch.object(
        unique_sdk.Message, "modify", autospec=True, side_effect=Exception("API Error")
    )
    def test_error_handling_modify_message(self, mock_modify):
        with pytest.raises(Exception, match="API Error"):
            self.service.modify_assistant_message("Modified message")

    @patch.object(unique_sdk.Message, "list", side_effect=Exception("History Error"))
    def test_error_handling_get_history(self, mock_list):
        with pytest.raises(Exception, match="History Error"):
            self.service.get_full_and_selected_history(100, 0.8, 10)

    @patch.object(
        unique_sdk.Message,
        "create",
        autospec=True,
        side_effect=Exception("Creation Error"),
    )
    def test_error_handling_create_message(self, mock_create):
        with pytest.raises(Exception, match="Creation Error"):
            self.service.create_assistant_message("New message")

    @pytest.mark.asyncio
    @patch.object(unique_sdk.Message, "modify_async", autospec=True)
    async def test_modify_assistant_message_async(self, mock_modify):
        # Test with update completedAt
        mock_modify.return_value = {
            "id": "test_message",
            "content": "Modified message",
            "role": "assistant",
            "chatId": "chatId123",
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

        result = await self.service.modify_assistant_message_async(
            content="Modified message",
            message_id="test_assistant_message",
            references=references,
            debug_info={},
            set_completed_at=True,
        )
        result = await self.service.modify_assistant_message_async(
            content="Modified message",
            message_id="test_assistant_message",
            references=references,
            debug_info={},
            set_completed_at=True,
        )

        assert isinstance(result, ChatMessage)
        assert result.content == "Modified message"
        assert result.role == ChatMessageRole.ASSISTANT
        assert isinstance(result, ChatMessage)
        assert result.content == "Modified message"
        assert result.role == ChatMessageRole.ASSISTANT

        expected_calls = [
            mock.call(
                user_id="test_user",
                company_id="test_company",
                id="test_assistant_message",
                chatId="test_chat",
                text="Modified message",
                originalText=None,
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
                completedAt=mocked_datetime,
            )
        ]
        mock_modify.assert_has_calls(expected_calls)
        mock_modify.reset_mock()

        # Test without update completedAt
        mock_modify.return_value = {
            "id": "test_message",
            "chatId": "chatId123",
            "content": "Modified message",
            "role": "assistant",
        }

        result = await self.service.modify_assistant_message_async(
            content="Modified message",
            message_id="test_assistant_message",
            references=references,
            debug_info={},
        )

        assert isinstance(result, ChatMessage)
        assert result.content == "Modified message"
        assert result.role == ChatMessageRole.ASSISTANT

        expected_calls = [
            mock.call(
                user_id="test_user",
                company_id="test_company",
                id="test_assistant_message",
                chatId="test_chat",
                text="Modified message",
                originalText=None,
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
                completedAt=None,
            )
        ]
        mock_modify.assert_has_calls(expected_calls)

    @pytest.mark.asyncio
    @patch.object(unique_sdk.Message, "list_async", autospec=True)
    async def test_get_history_async(self, mock_list):
        mock_list.return_value = {
            "object": "list",
            "data": [
                {
                    "id": "message1",
                    "text": "Message 1",
                    "role": "assistant",
                    "chatId": "chatId123",
                    "originalText": "originText",
                    "createdAt": mocked_datetime,
                    "updatedAt": mocked_datetime,
                    "completedAt": mocked_datetime,
                },
                {
                    "id": "message2",
                    "text": "Message 2",
                    "role": "user",
                    "chatId": "chatId123",
                    "originalText": "originText",
                    "createdAt": mocked_datetime,
                    "updatedAt": mocked_datetime,
                    "completedAt": mocked_datetime,
                },
                {
                    "id": "message3",
                    "text": "Message 3",
                    "role": "assistant",
                    "chatId": "chatId123",
                    "originalText": "originText",
                    "createdAt": mocked_datetime,
                    "updatedAt": mocked_datetime,
                    "completedAt": mocked_datetime,
                },
                {
                    "id": "message4",
                    "text": "Message 4",
                    "role": "user",
                    "chatId": "chatId123",
                    "originalText": "originText",
                    "createdAt": mocked_datetime,
                    "updatedAt": mocked_datetime,
                    "completedAt": mocked_datetime,
                },
            ],
        }

        (
            full_history,
            selected_history,
        ) = await self.service.get_full_and_selected_history_async(
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

    @pytest.mark.asyncio
    @patch.object(unique_sdk.Message, "create_async", autospec=True)
    async def test_create_assistant_message_async(self, mock_create):
        # Test with update completedAt
        mock_create.return_value = {
            "content": "New assistant message",
            "chat_id": "chatId123",
            "role": "ASSISTANT",
            "originalText": "originText",
            "createdAt": mocked_datetime,
            "updatedAt": mocked_datetime,
            "completedAt": mocked_datetime,
        }

        result = await self.service.create_assistant_message_async(
            content="New assistant message",
            references=[],
            debug_info={},
            set_completed_at=True,
        )
        result = await self.service.create_assistant_message_async(
            content="New assistant message",
            references=[],
            debug_info={},
            set_completed_at=True,
        )

        assert isinstance(result, ChatMessage)
        assert result.content == "New assistant message"
        assert result.role == ChatMessageRole.ASSISTANT.value
        assert isinstance(result, ChatMessage)
        assert result.content == "New assistant message"
        assert result.role == ChatMessageRole.ASSISTANT.value

        expected_calls = [
            mock.call(
                user_id="test_user",
                company_id="test_company",
                chatId="test_chat",
                assistantId="test_assistant",
                text="New assistant message",
                originalText="New assistant message",
                role="ASSISTANT",
                references=[],
                debugInfo={},
                completedAt=mocked_datetime,
            )
        ]
        mock_create.assert_has_calls(expected_calls)
        mock_create.reset_mock()

        # Test without update completedAt
        mock_create.return_value = {
            "content": "New assistant message",
            "role": "assistant",
            "chatId": "chatId123",
        }

        result = await self.service.create_assistant_message_async(
            content="New assistant message", references=[], debug_info={}
        )

        assert isinstance(result, ChatMessage)
        assert result.content == "New assistant message"
        assert result.role == ChatMessageRole.ASSISTANT

    @patch.object(unique_sdk.MessageAssessment, "create", autospec=True)
    def test_create_message_assessment(self, mock_create):
        mock_create.return_value = {
            "id": "test_assessment",
            "messageId": "msg_123",
            "status": "DONE",
            "explanation": "Test explanation",
            "label": "RED",
            "type": "HALLUCINATION",
            "isVisible": True,
            "createdAt": mocked_datetime,
            "updatedAt": mocked_datetime,
            "object": "message_assessment",
        }

        result = self.service.create_message_assessment(
            assistant_message_id="test_message",
            status=ChatMessageAssessmentStatus.DONE,
            explanation="Test explanation",
            label=ChatMessageAssessmentLabel.RED,
            type=ChatMessageAssessmentType.HALLUCINATION,
            is_visible=True,
        )

        assert isinstance(result, ChatMessageAssessment)
        assert result.status == ChatMessageAssessmentStatus.DONE.name
        assert result.explanation == "Test explanation"
        assert result.label == ChatMessageAssessmentLabel.RED.name
        assert result.type == ChatMessageAssessmentType.HALLUCINATION.name
        assert result.is_visible is True

        mock_create.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            messageId="test_message",
            status="DONE",
            explanation="Test explanation",
            label="RED",
            type="HALLUCINATION",
            isVisible=True,
            title=None,
        )

    @patch.object(unique_sdk.MessageAssessment, "modify", autospec=True)
    def test_modify_message_assessment(self, mock_modify):
        mock_modify.return_value = {
            "id": "test_assessment",
            "messageId": "msg_123",
            "status": "DONE",
            "explanation": "Modified explanation",
            "label": "GREEN",
            "type": "HALLUCINATION",
            "isVisible": True,
            "createdAt": mocked_datetime,
            "updatedAt": mocked_datetime,
            "completedAt": mocked_datetime,
            "object": "message_assessment",
        }

        result = self.service.modify_message_assessment(
            assistant_message_id="test_message",
            status=ChatMessageAssessmentStatus.DONE,
            explanation="Modified explanation",
            label=ChatMessageAssessmentLabel.GREEN,
            type=ChatMessageAssessmentType.HALLUCINATION,
            title="Test title",
        )

        assert isinstance(result, ChatMessageAssessment)
        assert result.status == ChatMessageAssessmentStatus.DONE.name
        assert result.explanation == "Modified explanation"
        assert result.label == ChatMessageAssessmentLabel.GREEN.name
        assert result.type == ChatMessageAssessmentType.HALLUCINATION.name

        mock_modify.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            messageId="test_message",
            status="DONE",
            explanation="Modified explanation",
            label="GREEN",
            type="HALLUCINATION",
            title="Test title",
        )

    @pytest.mark.asyncio
    @patch.object(
        unique_sdk.Message,
        "modify_async",
        autospec=True,
        side_effect=Exception("API Error"),
    )
    async def test_error_handling_modify_message_async(self, mock_modify):
        with pytest.raises(Exception, match="API Error"):
            await self.service.modify_assistant_message_async("Modified message")

    @pytest.mark.asyncio
    @patch.object(unique_sdk.MessageAssessment, "create_async", autospec=True)
    async def test_create_message_assessment_async(self, mock_create):
        mock_response = {
            "id": "test_assessment",
            "messageId": "msg_123",
            "status": "DONE",
            "explanation": "Test explanation",
            "label": "RED",
            "type": "HALLUCINATION",
            "isVisible": True,
            "createdAt": mocked_datetime,
            "updatedAt": mocked_datetime,
            "object": "message_assessment",
            "title": None,
        }

        mock_create.return_value = mock_response

        result = await self.service.create_message_assessment_async(
            assistant_message_id="test_message",
            status=ChatMessageAssessmentStatus.DONE,
            explanation="Test explanation",
            label=ChatMessageAssessmentLabel.RED,
            type=ChatMessageAssessmentType.HALLUCINATION,
            is_visible=True,
        )

        assert isinstance(result, ChatMessageAssessment)
        assert result.status == ChatMessageAssessmentStatus.DONE.name
        assert result.explanation == "Test explanation"
        assert result.label == ChatMessageAssessmentLabel.RED.name
        assert result.type == ChatMessageAssessmentType.HALLUCINATION.name
        assert result.is_visible is True

        mock_create.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            messageId="test_message",
            status="DONE",
            explanation="Test explanation",
            label="RED",
            type="HALLUCINATION",
            isVisible=True,
            title=None,
        )

    @pytest.mark.asyncio
    @patch.object(
        unique_sdk.Message, "list_async", side_effect=Exception("History Error")
    )
    async def test_error_handling_get_history_async(self, mock_list):
        with pytest.raises(Exception, match="History Error"):
            await self.service.get_full_and_selected_history_async(100, 0.8, 10)

    @patch.object(unique_sdk.MessageAssessment, "modify_async", autospec=True)
    async def test_modify_message_assessment_async(self, mock_modify):
        mock_response = {
            "id": "test_assessment",
            "messageId": "msg_123",
            "status": "DONE",
            "explanation": "Modified explanation",
            "label": "GREEN",
            "type": "HALLUCINATION",
            "isVisible": True,
            "createdAt": mocked_datetime,
            "updatedAt": mocked_datetime,
            "object": "message_assessment",
        }

        mock_modify.return_value = mock_response

        result = await self.service.modify_message_assessment_async(
            assistant_message_id="test_message",
            status=ChatMessageAssessmentStatus.DONE,
            explanation="Modified explanation",
            label=ChatMessageAssessmentLabel.GREEN,
            type=ChatMessageAssessmentType.HALLUCINATION,
            title="Test title",
        )

        assert isinstance(result, ChatMessageAssessment)
        assert result.status == ChatMessageAssessmentStatus.DONE.name
        assert result.explanation == "Modified explanation"
        assert result.label == ChatMessageAssessmentLabel.GREEN.name
        assert result.type == ChatMessageAssessmentType.HALLUCINATION.name

        mock_modify.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            messageId="test_message",
            status="DONE",
            explanation="Modified explanation",
            title="Test title",
            label="GREEN",
            type="HALLUCINATION",
        )

    @pytest.mark.asyncio
    @patch.object(
        unique_sdk.Message,
        "create_async",
        autospec=True,
        side_effect=Exception("Creation Error"),
    )
    async def test_error_handling_create_message_async(self, mock_create):
        with pytest.raises(Exception, match="Creation Error"):
            await self.service.create_assistant_message_async("New message")

    def test_init_with_chat_event(self):
        """Test initialization with ChatEvent"""
        chat_event = get_event_obj(
            user_id="test_user",
            company_id="test_company",
            chat_id="test_chat",
            assistant_id="test_assistant",
        )
        service = ChatService(chat_event)

        assert service.company_id == "test_company"
        assert service.user_id == "test_user"
        assert service.assistant_message_id == chat_event.payload.assistant_message.id
        assert service.user_message_id == chat_event.payload.user_message.id
        assert service.chat_id == "test_chat"
        assert service.assistant_id == "test_assistant"
        assert service.user_message_text == chat_event.payload.user_message.text

    def test_init_with_event(self):
        """Test initialization with Event"""
        event = Event(
            id="test-id",
            company_id="test_company",
            user_id="test_user",
            event=EventName.EXTERNAL_MODULE_CHOSEN,
            payload=EventPayload(
                name="module",
                description="description",
                configuration={},
                assistant_message=EventAssistantMessage(
                    id="asst_msg_id",
                    created_at="2021-01-01T00:00:00Z",
                ),
                user_message=EventUserMessage(
                    id="user_msg_id",
                    text="Hello user",
                    original_text="Hello user",
                    created_at="2021-01-01T00:00:00Z",
                    language="english",
                ),
                chat_id="test_chat",
                assistant_id="test_assistant",
            ),
        )
        service = ChatService(event)

        assert service.company_id == "test_company"
        assert service.user_id == "test_user"
        assert service.assistant_message_id == "asst_msg_id"
        assert service.user_message_id == "user_msg_id"
        assert service.chat_id == "test_chat"
        assert service.assistant_id == "test_assistant"
        assert service.user_message_text == "Hello user"

    @patch("unique_toolkit.services.chat_service.stream_complete_with_references")
    def test_stream_complete_to_chat(self, mock_stream_complete):
        """Test stream_complete method delegates correctly to function"""
        mock_stream_complete.return_value = LanguageModelStreamResponse(
            message=LanguageModelStreamResponseMessage(
                id="id",
                previous_message_id="previous_message_id",
                role=LanguageModelMessageRole.ASSISTANT,
                text="test",
            )
        )
        messages = LanguageModelMessages([])
        model_name = LanguageModelName.AZURE_GPT_4_0613
        content_chunks = [
            ContentChunk(id="1", chunk_id="1", key="test", order=1, text="test")
        ]

        self.service.stream_complete(
            messages=messages, model_name=model_name, content_chunks=content_chunks
        )

        mock_stream_complete.assert_called_once_with(
            company_id="test_company",
            user_id="test_user",
            assistant_message_id="assistant_message_id",
            user_message_id="user_message_id",
            chat_id="test_chat",
            assistant_id="test_assistant",
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            debug_info={},
            temperature=0.0,
            timeout=240000,
            tools=None,
            start_text=None,
            other_options=None,
        )

    @pytest.mark.asyncio
    @patch("unique_toolkit.services.chat_service.stream_complete_with_references_async")
    async def test_stream_complete_to_chat_async(self, mock_stream_complete_async):
        """Test stream_complete_async method delegates correctly to function"""
        mock_stream_complete_async.return_value = LanguageModelStreamResponse(
            message=LanguageModelStreamResponseMessage(
                id="id",
                previous_message_id="previous_message_id",
                role=LanguageModelMessageRole.ASSISTANT,
                text="test",
            )
        )
        messages = LanguageModelMessages([])
        model_name = LanguageModelName.AZURE_GPT_4_0613
        content_chunks = [
            ContentChunk(id="1", chunk_id="1", key="test", order=1, text="test")
        ]

        await self.service.stream_complete_async(
            messages=messages, model_name=model_name, content_chunks=content_chunks
        )

        mock_stream_complete_async.assert_called_once_with(
            company_id="test_company",
            user_id="test_user",
            assistant_message_id="assistant_message_id",
            user_message_id="user_message_id",
            chat_id="test_chat",
            assistant_id="test_assistant",
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            debug_info=None,
            temperature=0.0,
            timeout=240000,
            tools=None,
            start_text=None,
            other_options=None,
        )

    @patch.object(unique_sdk.Integrated, "chat_stream_completion")
    def test_stream_complete(self, mock_stream_complete):
        mock_stream_complete.return_value = {
            "message": {
                "id": "test_message",
                "previousMessageId": "test_previous_message",
                "role": "ASSISTANT",
                "text": "Streamed response",
                "originalText": "Streamed response original",
            }
        }
        messages = LanguageModelMessages([])
        model_name = LanguageModelName.AZURE_GPT_4_0613
        content_chunks = [
            ContentChunk(id="1", chunk_id="1", key="test", order=1, text="test")
        ]

        result = self.service.stream_complete(messages, model_name, content_chunks)

        assert isinstance(result, LanguageModelStreamResponse)
        assert result.message.text == "Streamed response"
        mock_stream_complete.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(unique_sdk.Integrated, "chat_stream_completion")
    async def test_stream_complete_with_other_options(self, mock_stream_complete):
        mock_stream_complete.return_value = {
            "message": {
                "id": "test_message",
                "previousMessageId": "test_previous_message",
                "role": "ASSISTANT",
                "text": "Streamed response",
                "originalText": "Streamed response original",
            }
        }
        messages = LanguageModelMessages([])
        model_name = LanguageModelName.AZURE_GPT_4_0613
        other_options = {"presence_penalty": 0.6, "frequency_penalty": 0.8}

        result = self.service.stream_complete(
            messages, model_name, content_chunks=None, other_options=other_options
        )

        assert isinstance(result, LanguageModelStreamResponse)
        assert result.message.text == "Streamed response"
        mock_stream_complete.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            assistantMessageId="assistant_message_id",
            userMessageId="user_message_id",
            messages=[],
            chatId="test_chat",
            searchContext=None,
            model=model_name.name,
            timeout=240000,
            assistantId="test_assistant",
            debugInfo={},
            options={
                "temperature": 0.0,
                "presence_penalty": 0.6,
                "frequency_penalty": 0.8,
            },
            startText=None,
        )

    @pytest.mark.asyncio
    @patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
    async def test_stream_complete_async_with_other_options(self, mock_stream_complete):
        mock_stream_complete.return_value = {
            "message": {
                "id": "test_message",
                "previousMessageId": "test_previous_message",
                "role": "ASSISTANT",
                "text": "Streamed response",
                "originalText": "Streamed response original",
            }
        }
        messages = LanguageModelMessages([])
        model_name = LanguageModelName.AZURE_GPT_4_0613
        other_options = {"presence_penalty": 0.6, "frequency_penalty": 0.8}

        result = await self.service.stream_complete_async(
            messages, model_name, other_options=other_options
        )

        assert isinstance(result, LanguageModelStreamResponse)
        assert result.message.text == "Streamed response"
        mock_stream_complete.assert_awaited_once_with(
            user_id="test_user",
            company_id="test_company",
            assistantMessageId="assistant_message_id",
            userMessageId="user_message_id",
            messages=[],
            chatId="test_chat",
            searchContext=None,
            model=model_name.name,
            timeout=240000,
            assistantId="test_assistant",
            debugInfo={},
            options={
                "temperature": 0.0,
                "presence_penalty": 0.6,
                "frequency_penalty": 0.8,
            },
            startText=None,
        )

    @patch.object(unique_sdk.Integrated, "chat_stream_completion")
    def test_stream_complete_with_custom_model(self, mock_stream_complete):
        mock_stream_complete.return_value = {
            "message": {
                "id": "test_message",
                "previousMessageId": "test_previous_message",
                "role": "ASSISTANT",
                "text": "Streamed response",
                "originalText": "Streamed response original",
            }
        }
        messages = LanguageModelMessages([])
        model_name = "My Custom Model"

        result = self.service.stream_complete(messages, model_name)

        assert isinstance(result, LanguageModelStreamResponse)
        assert result.message.text == "Streamed response"
        mock_stream_complete.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            assistantMessageId="assistant_message_id",
            userMessageId="user_message_id",
            messages=[],
            chatId="test_chat",
            searchContext=None,
            model=model_name,
            timeout=240000,
            assistantId="test_assistant",
            debugInfo={},
            options={"temperature": 0.0},
            startText=None,
        )

    @patch.object(unique_sdk.Integrated, "chat_stream_completion")
    def test_stream_complete_with_tool(self, mock_stream):
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        mock_stream.return_value = {
            "message": {
                "id": "test_stream_id",
                "previousMessageId": "test_previous_message_id",
                "role": "ASSISTANT",
                "text": "Streamed response",
                "originalText": "Streamed response original",
            },
            "toolCalls": [
                {
                    "id": "test_tool_id",
                    "name": "get_weather",
                    "arguments": '{"location": "London, UK", "unit": "celsius"}',
                }
            ],
        }

        response = self.service.stream_complete(
            messages=messages,
            model_name=DEFAULT_GPT_4o,
            tools=[mock_tool],
        )

        assert response.tool_calls is not None
        assert response.tool_calls[0].name == "get_weather"
        arguments = response.tool_calls[0].arguments
        assert arguments is not None
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        assert "London, UK" in arguments.values()

    @pytest.mark.asyncio
    @patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
    async def test_stream_complete_async(self, mock_stream_complete):
        mock_stream_complete.return_value = {
            "message": {
                "id": "test_message",
                "previousMessageId": "test_previous_message",
                "role": "ASSISTANT",
                "text": "Streamed response",
                "originalText": "Streamed response original",
            }
        }
        messages = LanguageModelMessages([])
        model_name = LanguageModelName.AZURE_GPT_4_0613
        content_chunks = [
            ContentChunk(id="1", chunk_id="1", key="test", order=1, text="test")
        ]

        result = await self.service.stream_complete_async(
            messages, model_name, content_chunks
        )

        assert isinstance(result, LanguageModelStreamResponse)
        assert result.message.text == "Streamed response"
        mock_stream_complete.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
    async def test_stream_complete_async_with_custom_model(self, mock_stream_complete):
        mock_stream_complete.return_value = {
            "message": {
                "id": "test_message",
                "previousMessageId": "test_previous_message",
                "role": "ASSISTANT",
                "text": "Streamed response",
                "originalText": "Streamed response original",
            }
        }
        messages = LanguageModelMessages([])
        model_name = "My custom model"

        result = await self.service.stream_complete_async(messages, model_name)

        assert isinstance(result, LanguageModelStreamResponse)
        assert result.message.text == "Streamed response"
        mock_stream_complete.assert_awaited_once_with(
            user_id="test_user",
            company_id="test_company",
            assistantMessageId="assistant_message_id",
            userMessageId="user_message_id",
            messages=[],
            chatId="test_chat",
            searchContext=None,
            model=model_name,
            timeout=240000,
            assistantId="test_assistant",
            debugInfo={},
            options={"temperature": 0.0},
            startText=None,
        )

    @pytest.mark.asyncio
    @patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
    async def test_error_handling_stream_complete_async(self, mock_stream_complete):
        mock_stream_complete.side_effect = Exception("Stream Error")
        with pytest.raises(Exception, match="Stream Error"):
            await self.service.stream_complete_async(
                LanguageModelMessages([]), LanguageModelName.AZURE_GPT_4_0613
            )

    @pytest.mark.asyncio
    @patch.object(unique_sdk.Integrated, "chat_stream_completion_async")
    async def test_stream_complete_with_tool_async(self, mock_stream):
        messages = LanguageModelMessages(
            [
                LanguageModelMessage(
                    role=LanguageModelMessageRole.USER,
                    content="What's the weather in New York?",
                )
            ]
        )

        mock_stream.return_value = {
            "message": {
                "id": "test_stream_id",
                "previousMessageId": "test_previous_message_id",
                "role": "ASSISTANT",
                "text": "Streamed response",
                "originalText": "Streamed response original",
            },
            "toolCalls": [
                {
                    "id": "test_tool_id",
                    "name": "get_weather",
                    "arguments": '{"location": "London, UK", "unit": "celsius"}',
                }
            ],
        }

        response = await self.service.stream_complete_async(
            messages=messages,
            model_name=DEFAULT_GPT_4o,
            tools=[mock_tool],
        )

        assert response.tool_calls is not None
        assert response.tool_calls[0].name == "get_weather"
        arguments = response.tool_calls[0].arguments
        assert arguments is not None
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        assert "London, UK" in arguments.values()
