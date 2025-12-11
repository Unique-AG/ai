"""
Tests for loop_runner helpers module.

This file contains tests for the helper functions used by loop runners,
specifically for Qwen model detection and tool instruction injection.
"""

import pytest

from unique_toolkit.agentic.loop_runner.helpers import (
    _QWEN__FORCED_TOOL_CALL_INSTRUCTION,
    append_qwen_forced_tool_call_instruction,
    is_qwen_model,
)
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)


# is_qwen_model Tests
class TestIsQwenModel:
    @pytest.mark.ai
    def test_is_qwen_model__returns_true__for_qwen_3_model(self) -> None:
        """
        Purpose: Verify is_qwen_model correctly identifies Qwen 3 model.
        Why this matters: Qwen models require special handling for tool calls.
        """
        # Arrange
        model_info = LanguageModelInfo.from_name(LanguageModelName.LITELLM_QWEN_3)

        # Act
        result = is_qwen_model(model_info)

        # Assert
        assert result is True

    @pytest.mark.ai
    def test_is_qwen_model__returns_true__for_qwen_3_thinking_model(self) -> None:
        """
        Purpose: Verify is_qwen_model correctly identifies Qwen 3 Thinking model.
        Why this matters: Qwen thinking model also needs special tool call handling.
        """
        # Arrange
        model_info = LanguageModelInfo.from_name(
            LanguageModelName.LITELLM_QWEN_3_THINKING
        )

        # Act
        result = is_qwen_model(model_info)

        # Assert
        assert result is True

    @pytest.mark.ai
    def test_is_qwen_model__returns_false__for_gpt_model(self) -> None:
        """
        Purpose: Verify is_qwen_model returns False for GPT models.
        Why this matters: GPT models should not receive Qwen-specific handling.
        """
        # Arrange
        model_info = LanguageModelInfo.from_name(
            LanguageModelName.AZURE_GPT_4o_2024_0513
        )

        # Act
        result = is_qwen_model(model_info)

        # Assert
        assert result is False

    @pytest.mark.ai
    def test_is_qwen_model__returns_false__for_none(self) -> None:
        """
        Purpose: Verify is_qwen_model handles None input.
        Why this matters: Function should handle missing model gracefully.
        """
        # Act
        result = is_qwen_model(None)

        # Assert
        assert result is False

    @pytest.mark.ai
    def test_is_qwen_model__returns_true__for_string_containing_qwen(self) -> None:
        """
        Purpose: Verify is_qwen_model returns True for string containing 'qwen'.
        Why this matters: Function should detect Qwen models from string names.
        """
        # Act
        result = is_qwen_model("qwen-3")

        # Assert
        assert result is True

    @pytest.mark.ai
    def test_is_qwen_model__returns_true__for_string_containing_qwen_case_insensitive(
        self,
    ) -> None:
        """
        Purpose: Verify is_qwen_model handles case-insensitive string matching.
        Why this matters: Model names may vary in capitalization.
        """
        # Act
        result_upper = is_qwen_model("QWEN-3")
        result_mixed = is_qwen_model("Qwen-3-Thinking")

        # Assert
        assert result_upper is True
        assert result_mixed is True

    @pytest.mark.ai
    def test_is_qwen_model__returns_false__for_string_not_containing_qwen(self) -> None:
        """
        Purpose: Verify is_qwen_model returns False for strings without 'qwen'.
        Why this matters: Non-Qwen model strings should not receive Qwen-specific handling.
        """
        # Act
        result = is_qwen_model("gpt-4o")

        # Assert
        assert result is False


# append_qwen_forced_tool_call_instruction Tests
class TestAppendQwenToolInstruction:
    @pytest.mark.ai
    def test_append_qwen_forced_tool_call_instruction__appends_to_last_user_message(
        self,
    ) -> None:
        """
        Purpose: Verify instruction is appended to the last user message.
        Why this matters: Qwen models need explicit tool call instruction in user message.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[
                LanguageModelSystemMessage(content="You are a helpful assistant."),
                LanguageModelUserMessage(content="Search for documents"),
            ]
        )

        # Act
        result = append_qwen_forced_tool_call_instruction(messages)

        # Assert
        assert len(result.root) == 2
        assert result.root[1].content == (
            "Search for documents" + _QWEN__FORCED_TOOL_CALL_INSTRUCTION
        )
        # System message should be unchanged
        assert result.root[0].content == "You are a helpful assistant."

    @pytest.mark.ai
    def test_append_qwen_forced_tool_call_instruction__finds_last_user_message_not_final(
        self,
    ) -> None:
        """
        Purpose: Verify instruction is appended to last user message even if not final.
        Why this matters: User message may not always be at the end of message list.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="First user message"),
                LanguageModelAssistantMessage(content="Assistant response"),
                LanguageModelUserMessage(content="Second user message"),
                LanguageModelAssistantMessage(content="Another response"),
            ]
        )

        # Act
        result = append_qwen_forced_tool_call_instruction(messages)

        # Assert
        # Should modify the last user message (index 2)
        assert isinstance(result.root[2].content, str)
        assert "Second user message" in result.root[2].content
        assert isinstance(result.root[2].content, str)
        assert _QWEN__FORCED_TOOL_CALL_INSTRUCTION in result.root[2].content
        # First user message should be unchanged
        assert result.root[0].content == "First user message"

    @pytest.mark.ai
    def test_append_qwen_forced_tool_call_instruction__preserves_original_messages(
        self,
    ) -> None:
        """
        Purpose: Verify original messages object is not mutated.
        Why this matters: Function should return new messages, not modify input.
        """
        # Arrange
        original_content = "Original user message"
        messages = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content=original_content),
            ]
        )

        # Act
        result = append_qwen_forced_tool_call_instruction(messages)

        # Assert
        # Original should be unchanged
        assert messages.root[0].content == original_content
        # Result should have the instruction
        assert result.root[0].content != original_content

    @pytest.mark.ai
    def test_append_qwen_forced_tool_call_instruction__handles_no_user_messages(
        self,
    ) -> None:
        """
        Purpose: Verify function handles messages with no user message.
        Why this matters: Edge case where only system/assistant messages exist.
        """
        # Arrange
        messages = LanguageModelMessages(
            root=[
                LanguageModelSystemMessage(content="System prompt"),
                LanguageModelAssistantMessage(content="Assistant response"),
            ]
        )

        # Act
        result = append_qwen_forced_tool_call_instruction(messages)

        # Assert
        # Messages should be unchanged since no user message found
        assert len(result.root) == 2
        assert result.root[0].content == "System prompt"
        assert result.root[1].content == "Assistant response"

    @pytest.mark.ai
    def test_append_qwen_forced_tool_call_instruction__handles_empty_messages(
        self,
    ) -> None:
        """
        Purpose: Verify function handles empty message list.
        Why this matters: Edge case that should not raise an error.
        """
        # Arrange
        messages = LanguageModelMessages(root=[])

        # Act
        result = append_qwen_forced_tool_call_instruction(messages)

        # Assert
        assert len(result.root) == 0
