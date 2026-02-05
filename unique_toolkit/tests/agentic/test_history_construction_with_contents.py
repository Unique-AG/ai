import pytest

from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    limit_to_token_window,
)
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelUserMessage,
)


def test_limit_to_token_window_without_model():
    messages = LanguageModelMessages(
        root=[
            LanguageModelUserMessage(content="Short message 1"),
            LanguageModelUserMessage(content="Short message 2"),
            LanguageModelUserMessage(content="Very long message " * 100),
        ]
    )

    result = limit_to_token_window(messages, token_limit=100)

    assert len(result.root) < len(messages.root)
    assert len(result.root) > 0


@pytest.mark.ai
def test_limit_to_token_window_with_gpt_model():
    messages = LanguageModelMessages(
        root=[
            LanguageModelUserMessage(content="First message"),
            LanguageModelUserMessage(content="Second message"),
            LanguageModelUserMessage(content="Third message " * 50),
        ]
    )

    model_info = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_0513)

    result = limit_to_token_window(messages, token_limit=100, model_info=model_info)

    assert len(result.root) < len(messages.root)
    assert len(result.root) > 0


@pytest.mark.ai
def test_limit_to_token_window_with_qwen_model():
    messages = LanguageModelMessages(
        root=[
            LanguageModelUserMessage(content="你好世界"),
            LanguageModelUserMessage(content="这是一个测试"),
            LanguageModelUserMessage(content="非常长的消息 " * 50),
        ]
    )

    model_info = LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)

    result = limit_to_token_window(messages, token_limit=50, model_info=model_info)

    assert len(result.root) < len(messages.root)
    assert len(result.root) > 0
