"""
Unit tests for unique_toolkit.agentic.claude_agent.history

Naming convention: test_<function>_<scenario>_<expected>
"""

from __future__ import annotations

from unique_toolkit.agentic.claude_agent.history import format_history_as_text
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)


def _user(text: str) -> LanguageModelUserMessage:
    return LanguageModelUserMessage(content=text)


def _assistant(text: str) -> LanguageModelAssistantMessage:
    return LanguageModelAssistantMessage(content=text)


def _tool(text: str) -> LanguageModelToolMessage:
    return LanguageModelToolMessage(content=text, tool_call_id="tc-1", name="search")


# ─────────────────────────────────────────────────────────────────────────────
# format_history_as_text
# ─────────────────────────────────────────────────────────────────────────────


class TestFormatHistoryAsText:
    def test_format_history_empty_list_returns_empty_string(self) -> None:
        assert format_history_as_text([], max_interactions=4) == ""

    def test_format_history_zero_max_interactions_returns_empty_string(self) -> None:
        messages = [_user("hi"), _assistant("hello")]
        assert format_history_as_text(messages, max_interactions=0) == ""

    def test_format_history_single_interaction(self) -> None:
        messages = [_user("What is 2+2?"), _assistant("It is 4.")]
        result = format_history_as_text(messages, max_interactions=4)
        assert "User: What is 2+2?" in result
        assert "Assistant: It is 4." in result

    def test_format_history_respects_max_interactions(self) -> None:
        messages = []
        for i in range(5):
            messages.append(_user(f"Question {i}"))
            messages.append(_assistant(f"Answer {i}"))

        result = format_history_as_text(messages, max_interactions=2)

        # Only the last 2 pairs should appear
        assert "Question 3" in result
        assert "Answer 3" in result
        assert "Question 4" in result
        assert "Answer 4" in result
        # Earlier pairs should be excluded
        assert "Question 0" not in result
        assert "Question 1" not in result
        assert "Question 2" not in result

    def test_format_history_skips_tool_messages(self) -> None:
        messages = [
            _user("Find me data"),
            _tool("search results here"),
            _assistant("Here is your data."),
        ]
        result = format_history_as_text(messages, max_interactions=4)
        assert "search results here" not in result
        assert "User: Find me data" in result
        assert "Assistant: Here is your data." in result

    def test_format_history_truncates_long_messages(self) -> None:
        long_text = "x" * 3000
        messages = [_user(long_text), _assistant("Short reply.")]
        result = format_history_as_text(messages, max_interactions=4)
        assert "... [truncated]" in result
        # The truncated portion should not contain the full original text
        assert long_text not in result

    def test_format_history_pairs_separated_by_blank_line(self) -> None:
        messages = [
            _user("First question"),
            _assistant("First answer"),
            _user("Second question"),
            _assistant("Second answer"),
        ]
        result = format_history_as_text(messages, max_interactions=4)
        assert "\n\n" in result

    def test_format_history_trailing_user_message_discarded(self) -> None:
        """An unpaired trailing user message (current turn) is not included."""
        messages = [
            _user("Old question"),
            _assistant("Old answer"),
            _user("Current question without reply"),
        ]
        result = format_history_as_text(messages, max_interactions=4)
        assert "Old question" in result
        assert "Current question without reply" not in result

    def test_format_history_multiple_pairs_correct_order(self) -> None:
        messages = [
            _user("First"),
            _assistant("First reply"),
            _user("Second"),
            _assistant("Second reply"),
        ]
        result = format_history_as_text(messages, max_interactions=4)
        first_pos = result.index("First")
        second_pos = result.index("Second")
        assert first_pos < second_pos
