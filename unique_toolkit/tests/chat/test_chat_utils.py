import pytest

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.chat.utils import convert_chat_history_to_injectable_string
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName


def test_convert_chat_history_to_injectable_string():
    history = [
        ChatMessage(
            id="1",
            role=ChatMessageRole.USER,
            text="What is Python?",
            chat_id="chat123",
        ),
        ChatMessage(
            id="2",
            role=ChatMessageRole.ASSISTANT,
            text="Python is a programming language.",
            chat_id="chat123",
        ),
    ]

    chat_strings, token_count = convert_chat_history_to_injectable_string(history)

    assert len(chat_strings) == 2
    assert "previous_question: What is Python?" in chat_strings[0]
    assert "previous_answer: Python is a programming language." in chat_strings[1]
    assert isinstance(token_count, int)
    assert token_count > 0


@pytest.mark.ai
def test_convert_chat_history_to_injectable_string_with_model():
    history = [
        ChatMessage(
            id="1",
            role=ChatMessageRole.USER,
            text="你好世界",
            chat_id="chat123",
        ),
        ChatMessage(
            id="2",
            role=ChatMessageRole.ASSISTANT,
            text="Hello world",
            chat_id="chat123",
        ),
    ]

    model_info = LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)

    chat_strings, token_count = convert_chat_history_to_injectable_string(
        history, model_info=model_info
    )

    assert len(chat_strings) == 2
    assert isinstance(token_count, int)
    assert token_count > 0
