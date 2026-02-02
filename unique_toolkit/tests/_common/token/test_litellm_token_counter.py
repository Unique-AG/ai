"""Tests for model-agnostic token counting service."""

import pytest
import tiktoken

from unique_toolkit._common.token import count_tokens_for_model
from unique_toolkit.content.utils import count_tokens as content_count_tokens
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

_TEST_TEXT = """Hello, how are you today? I'm working on a project that involves 
counting tokens for different language models. This includes models like GPT-4, 
Claude, and Qwen. 你好世界！这是一些中文文本。"""

_TEST_TEXT_SHORT = "Hello, how are you?"


@pytest.mark.ai
class TestTokenService:
    """Test the model-agnostic token counting service."""

    def test_openai_model_tiktoken_compatibility(self):
        model_info = LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_0806
        )

        service_count = count_tokens_for_model(_TEST_TEXT, model_info)

        encoder = tiktoken.get_encoding(model_info.encoder_name)
        tiktoken_count = len(encoder.encode(_TEST_TEXT))

        # LiteLLM wraps text in message format internally, adding ~10 tokens for formatting
        # Allow 25% difference to account for message overhead
        diff_percentage = abs(service_count - tiktoken_count) / tiktoken_count * 100
        assert diff_percentage <= 25.0, (
            f"Token count difference > 25%: service={service_count}, "
            f"tiktoken={tiktoken_count}, diff={diff_percentage:.2f}%"
        )

    def test_qwen_uses_custom_tokenizer(self):
        """Test that Qwen models use custom tokenizer, not tiktoken fallback."""
        model_info = LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)

        # Count with service (should use custom Qwen tokenizer)
        service_count = count_tokens_for_model(_TEST_TEXT, model_info)

        # Count with tiktoken (what we DON'T want)
        encoder = tiktoken.get_encoding("cl100k_base")
        tiktoken_count = len(encoder.encode(_TEST_TEXT))

        # These should be different (Qwen has different tokenization)
        assert service_count != tiktoken_count, (
            "Qwen token count matches tiktoken, suggesting custom tokenizer not used"
        )

        # Qwen should produce reasonable token counts
        assert service_count > 0
        assert service_count < len(_TEST_TEXT)  # Sanity check

    def test_deepseek_uses_custom_tokenizer(self):
        """Test that DeepSeek models use custom tokenizer."""
        model_info = LanguageModelInfo.from_name(LanguageModelName.LITELLM_DEEPSEEK_R1)

        # Count with service (should use custom DeepSeek tokenizer)
        service_count = count_tokens_for_model(_TEST_TEXT, model_info)

        # Count with tiktoken (what we DON'T want)
        encoder = tiktoken.get_encoding("cl100k_base")
        tiktoken_count = len(encoder.encode(_TEST_TEXT))

        # These should be different
        assert service_count != tiktoken_count, (
            "DeepSeek token count matches tiktoken, suggesting custom tokenizer not used"
        )

        # Sanity checks
        assert service_count > 0
        assert service_count < len(_TEST_TEXT)

    def test_empty_text_returns_zero(self):
        """Test that empty text returns 0 tokens."""
        model_info = LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_0806
        )
        assert count_tokens_for_model("", model_info) == 0
        assert count_tokens_for_model("   ", model_info) > 0  # Whitespace counts

    @pytest.mark.parametrize(
        "model_name",
        [
            LanguageModelName.AZURE_GPT_35_TURBO_0125,
            LanguageModelName.AZURE_GPT_4o_2024_0513,
            LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
            LanguageModelName.LITELLM_QWEN_3,
            LanguageModelName.LITELLM_QWEN_3_THINKING,
            LanguageModelName.LITELLM_DEEPSEEK_R1,
            LanguageModelName.LITELLM_DEEPSEEK_V3,
            LanguageModelName.ANTHROPIC_CLAUDE_SONNET_4,
            LanguageModelName.GEMINI_2_5_FLASH,
        ],
    )
    def test_various_models_produce_valid_counts(self, model_name):
        """Test that various models produce valid token counts."""
        model_info = LanguageModelInfo.from_name(model_name)
        count = count_tokens_for_model(_TEST_TEXT_SHORT, model_info)

        # Basic sanity checks
        assert count > 0, f"Model {model_name} returned 0 tokens"
        assert count < len(_TEST_TEXT_SHORT), (
            f"Model {model_name} token count > text length"
        )


@pytest.mark.ai
class TestBackwardCompatibility:
    """Test backward compatibility of updated count_tokens functions."""

    def test_content_utils_backward_compatibility(self):
        """Test that content.utils.count_tokens works without model_info (legacy)."""
        count = content_count_tokens(_TEST_TEXT_SHORT)

        encoder = tiktoken.get_encoding("cl100k_base")
        expected = len(encoder.encode(_TEST_TEXT_SHORT))
        assert count == expected

    def test_content_utils_with_custom_encoding(self):
        """Test content.utils.count_tokens with custom encoding (legacy)."""
        count = content_count_tokens(_TEST_TEXT_SHORT, encoding_model="o200k_base")

        # Should match tiktoken with o200k_base
        encoder = tiktoken.get_encoding("o200k_base")
        expected = len(encoder.encode(_TEST_TEXT_SHORT))
        assert count == expected


@pytest.mark.ai
class TestLiteLLMMapping:
    """Test the LiteLLM model name mapping."""

    def test_azure_models_mapped_correctly(self):
        """Test that Azure models are mapped to azure/ prefix."""
        assert (
            LanguageModelName.AZURE_GPT_4o_2024_0806.get_litellm_name()
            == "azure/gpt-4o"
        )
        assert (
            LanguageModelName.AZURE_GPT_35_TURBO_0125.get_litellm_name()
            == "azure/gpt-35-turbo"
        )
        assert (
            LanguageModelName.AZURE_GPT_4o_MINI_2024_0718.get_litellm_name()
            == "azure/gpt-4o-mini"
        )

    def test_qwen_models_mapped_correctly(self):
        """Test that Qwen models are mapped correctly."""
        assert (
            LanguageModelName.LITELLM_QWEN_3.get_litellm_name()
            == "qwen/qwen2-72b-instruct"
        )
        assert (
            LanguageModelName.LITELLM_QWEN_3_THINKING.get_litellm_name()
            == "qwen/qwen2-72b-instruct"
        )

    def test_deepseek_models_mapped_correctly(self):
        """Test that DeepSeek models are mapped correctly."""
        assert (
            LanguageModelName.LITELLM_DEEPSEEK_R1.get_litellm_name()
            == "deepseek/deepseek-reasoner"
        )
        assert (
            LanguageModelName.LITELLM_DEEPSEEK_V3.get_litellm_name()
            == "deepseek/deepseek-chat"
        )

    def test_claude_models_mapped_correctly(self):
        """Test that Claude models are mapped correctly."""
        result = LanguageModelName.ANTHROPIC_CLAUDE_SONNET_4.get_litellm_name()
        assert "claude" in result.lower()
        assert "anthropic" in result.lower() or result.startswith("claude")

    def test_gemini_models_mapped_correctly(self):
        """Test that Gemini models are mapped correctly."""
        result = LanguageModelName.GEMINI_2_5_FLASH.get_litellm_name()
        assert "gemini" in result.lower()
