import pytest

from unique_toolkit._common.experimental.write_up_agent.services.generation_handler.config import (
    GenerationHandlerConfig,
)
from unique_toolkit._common.experimental.write_up_agent.services.generation_handler.service import (
    GenerationHandler,
)
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName


@pytest.mark.ai
def test_generation_handler_token_counter_with_gpt():
    config = GenerationHandlerConfig(
        language_model=LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_0513
        )
    )

    handler = GenerationHandler(config=config, renderer=None)

    text = "Hello world"
    token_count = handler._token_counter(text)

    assert isinstance(token_count, int)
    assert token_count > 0


@pytest.mark.ai
def test_generation_handler_token_counter_with_qwen():
    config = GenerationHandlerConfig(
        language_model=LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)
    )

    handler = GenerationHandler(config=config, renderer=None)

    text = "你好世界"
    token_count = handler._token_counter(text)

    assert isinstance(token_count, int)
    assert token_count > 0


@pytest.mark.ai
def test_generation_handler_token_counter_with_deepseek():
    config = GenerationHandlerConfig(
        language_model=LanguageModelInfo.from_name(
            LanguageModelName.LITELLM_DEEPSEEK_V3
        )
    )

    handler = GenerationHandler(config=config, renderer=None)

    text = "Test message"
    token_count = handler._token_counter(text)

    assert isinstance(token_count, int)
    assert token_count > 0
