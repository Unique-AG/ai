from unittest.mock import patch

import pytest
import unique_sdk

from unique_toolkit.chat.state import ChatState
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
)
from unique_toolkit.language_model.service import LanguageModelService


class TestLanguageModelService:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.chat_state = ChatState(
            user_id="test_user",
            company_id="test_company",
            assistant_id="test_assistant",
            chat_id="test_chat",
        )
        self.service = LanguageModelService(self.chat_state)

    def test_complete(self):
        with patch.object(unique_sdk.ChatCompletion, "create") as mock_create:
            mock_create.return_value = {
                "choices": [
                    {
                        "index": 0,
                        "finishReason": "completed",
                        "message": {
                            "content": "Test response",
                            "role": "assistant",
                        },
                    }
                ]
            }
            messages = LanguageModelMessages([])
            model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106

            result = self.service.complete(messages, model_name)

            assert isinstance(result, LanguageModelResponse)
            assert result.choices[0].message.content == "Test response"
            mock_create.assert_called_once_with(
                company_id="test_company",
                model=model_name.name,
                messages=[],
                timeout=240000,
                temperature=0.0,
            )

    def test_stream_complete(self):
        with patch.object(
            unique_sdk.Integrated, "chat_stream_completion"
        ) as mock_stream_complete:
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
            model_name = LanguageModelName.AZURE_GPT_4_TURBO_1106
            content_chunks = [
                ContentChunk(id="1", chunk_id="1", key="test", order=1, text="test")
            ]

            result = self.service.stream_complete(messages, model_name, content_chunks)

            assert isinstance(result, LanguageModelStreamResponse)
            assert result.message.text == "Streamed response"
            mock_stream_complete.assert_called_once()

    def test_error_handling_complete(self):
        with patch.object(
            unique_sdk.ChatCompletion, "create", side_effect=Exception("API Error")
        ):
            with pytest.raises(Exception, match="API Error"):
                self.service.complete(
                    LanguageModelMessages([]), LanguageModelName.AZURE_GPT_4_TURBO_1106
                )

    def test_error_handling_stream_complete(self):
        with patch.object(
            unique_sdk.Integrated,
            "chat_stream_completion",
            side_effect=Exception("Stream Error"),
        ):
            with pytest.raises(Exception, match="Stream Error"):
                self.service.stream_complete(
                    LanguageModelMessages([]), LanguageModelName.AZURE_GPT_4_TURBO_1106
                )
