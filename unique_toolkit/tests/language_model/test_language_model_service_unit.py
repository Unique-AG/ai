from unittest.mock import patch

import pytest

from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
)
from unique_toolkit.language_model.service import LanguageModelService


class TestLanguageModelServiceUnit:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.chat_event = ChatEvent(
            id="test-id",
            event=EventName.EXTERNAL_MODULE_CHOSEN,
            user_id="test_user",
            company_id="test_company",
            payload=ChatEventPayload(
                assistant_id="test_assistant",
                chat_id="test_chat",
                name="module",
                description="module_description",
                configuration={},
                user_message=ChatEventUserMessage(
                    id="user_message_id",
                    text="Test user message",
                    created_at="2021-01-01T00:00:00Z",
                    language="DE",
                    original_text="Test user message",
                ),
                assistant_message=ChatEventAssistantMessage(
                    id="assistant_message_id", created_at="2021-01-01T00:00:00Z"
                ),
                metadata_filter={},
            ),
        )
        self.service = LanguageModelService(self.chat_event)

    def test_init_with_chat_event(self):
        """Test initialization with ChatEvent"""
        service = LanguageModelService(self.chat_event)

        assert service.company_id == "test_company"
        assert service.user_id == "test_user"
        assert (
            service.assistant_message_id == self.chat_event.payload.assistant_message.id
        )
        assert service.user_message_id == self.chat_event.payload.user_message.id
        assert service.chat_id == "test_chat"
        assert service.assistant_id == "test_assistant"

    @patch("unique_toolkit.language_model.service.complete")
    def test_complete(self, mock_complete):
        """Test complete method delegates correctly to function"""
        mock_complete.return_value = LanguageModelResponse(choices=[])
        messages = LanguageModelMessages([])
        model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106

        self.service.complete(messages=messages, model_name=model_name)

        mock_complete.assert_called_once_with(
            company_id="test_company",
            messages=messages,
            model_name=model_name,
            temperature=0.0,
            timeout=240000,
            tools=None,
            other_options=None,
        )

    @patch("unique_toolkit.language_model.service.stream_complete")
    def test_stream_complete(self, mock_stream_complete):
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
        model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106
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
    @patch("unique_toolkit.language_model.service.complete_async")
    async def test_complete_async(self, mock_complete_async):
        """Test complete_async method delegates correctly to function"""
        mock_complete_async.return_value = LanguageModelResponse(choices=[])
        messages = LanguageModelMessages([])
        model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106

        await self.service.complete_async(messages=messages, model_name=model_name)

        mock_complete_async.assert_called_once_with(
            company_id="test_company",
            messages=messages,
            model_name=model_name,
            temperature=0.0,
            timeout=240000,
            tools=None,
            other_options=None,
        )

    @pytest.mark.asyncio
    @patch("unique_toolkit.language_model.service.stream_complete_async")
    async def test_stream_complete_async(self, mock_stream_complete_async):
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
        model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106
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
            debug_info={},
            temperature=0.0,
            timeout=240000,
            tools=None,
            start_text=None,
            other_options=None,
        )
