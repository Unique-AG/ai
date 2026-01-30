import pytest

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.chat.utils import convert_chat_history_to_injectable_string
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName


class TestConvertChatHistoryToInjectableString:
    @pytest.mark.ai
    def test_converts_history_without_model_info(self):
        """Backward compatibility: works without model_info parameter."""
        history = [
            ChatMessage(
                id="1",
                role=ChatMessageRole.USER,
                text="Hello",
                chat_id="chat123",
            ),
            ChatMessage(
                id="2",
                role=ChatMessageRole.ASSISTANT,
                text="Hi there!",
                chat_id="chat123",
            ),
        ]

        result, token_count = convert_chat_history_to_injectable_string(history)

        assert len(result) == 2
        assert result[0] == "previous_question: Hello"
        assert result[1] == "previous_answer: Hi there!"
        assert token_count > 0

    @pytest.mark.ai
    def test_converts_history_with_model_info(self):
        """Model-aware token counting with model_info parameter."""
        model_info = LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_0513
        )
        history = [
            ChatMessage(
                id="1",
                role=ChatMessageRole.USER,
                text="What is the weather?",
                chat_id="chat123",
            ),
            ChatMessage(
                id="2",
                role=ChatMessageRole.ASSISTANT,
                text="The weather is sunny.",
                chat_id="chat123",
            ),
        ]

        result, token_count = convert_chat_history_to_injectable_string(
            history, model_info=model_info
        )

        assert len(result) == 2
        assert "previous_question:" in result[0]
        assert "previous_answer:" in result[1]
        assert token_count > 0

    @pytest.mark.ai
    def test_returns_empty_for_empty_history(self):
        """Returns empty list and zero tokens for empty history."""
        result, token_count = convert_chat_history_to_injectable_string([])

        assert result == []
        assert token_count == 0
