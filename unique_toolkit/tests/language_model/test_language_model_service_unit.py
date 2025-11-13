from unittest.mock import patch

import pytest

from unique_toolkit.app.schemas import (
    BaseEvent,
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
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
        assert service.chat_id == "test_chat"
        assert service.assistant_id == "test_assistant"

    def test_init_with_direct_params(self):
        """Test initialization with direct parameters"""
        service = LanguageModelService(
            company_id="direct_company",
            user_id="direct_user",
        )

        assert service.company_id == "direct_company"
        assert service.user_id == "direct_user"
        assert service.chat_id is None
        assert service.assistant_id is None

    def test_init_with_base_event(self):
        """Test initialization with BaseEvent"""
        base_event = BaseEvent(
            id="test-id",
            company_id="base_company",
            user_id="base_user",
            event=EventName.EXTERNAL_MODULE_CHOSEN,
        )
        service = LanguageModelService(base_event)

        assert service.company_id == "base_company"
        assert service.user_id == "base_user"
        assert service.chat_id is None
        assert service.assistant_id is None

    def test_init_with_no_params(self):
        """Test initialization with no parameters should raise ValueError"""
        with pytest.raises(ValueError):
            LanguageModelService()

    @patch("unique_toolkit.language_model.service.complete")
    def test_complete(self, mock_complete):
        """Test complete method delegates correctly to function"""
        mock_complete.return_value = LanguageModelResponse(choices=[])
        messages = LanguageModelMessages([])
        model_name = LanguageModelName.AZURE_GPT_4_0613

        self.service.complete(messages=messages, model_name=model_name)

        mock_complete.assert_called_once_with(
            user_id="test_user",
            company_id="test_company",
            messages=messages,
            model_name=model_name,
            temperature=0.0,
            timeout=240000,
            tools=None,
            other_options=None,
            structured_output_enforce_schema=False,
            structured_output_model=None,
        )

    @pytest.mark.asyncio
    @patch("unique_toolkit.language_model.service.complete_async")
    async def test_complete_async(self, mock_complete_async):
        """Test complete_async method delegates correctly to function"""
        mock_complete_async.return_value = LanguageModelResponse(choices=[])
        messages = LanguageModelMessages([])
        model_name = LanguageModelName.AZURE_GPT_4_0613

        await self.service.complete_async(messages=messages, model_name=model_name)

        mock_complete_async.assert_called_once_with(
            company_id="test_company",
            user_id="test_user",
            messages=messages,
            model_name=model_name,
            temperature=0.0,
            timeout=240000,
            tools=None,
            other_options=None,
            structured_output_enforce_schema=False,
            structured_output_model=None,
        )
