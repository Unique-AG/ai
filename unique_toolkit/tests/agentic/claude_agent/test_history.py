"""
Unit tests for unique_toolkit.agentic.claude_agent.history

Naming convention: test_<function>_<scenario>_<expected>
"""

from __future__ import annotations

from unique_toolkit.agentic.claude_agent.history import format_history_as_text
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelFunctionCall,
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

    def test_format_history_renders_tool_messages_inline(self) -> None:
        """Tool messages appear inline between user and assistant lines (B9)."""
        messages = [
            _user("Find me data"),
            _tool("search results here"),
            _assistant("Here is your data."),
        ]
        result = format_history_as_text(messages, max_interactions=4)
        assert "search results here" in result
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

    def test_format_history_includes_tool_messages_with_args_and_result(self) -> None:
        """[Tool: name(args)] label and truncated result both appear in output (B9)."""
        fn_call = LanguageModelFunctionCall(
            id="tc-42",
            function=LanguageModelFunction(
                id="fn-1",
                name="search_knowledge_base",
                arguments={"search_query": "ECB rate 2026"},
            ),
        )
        intermediate_assistant = LanguageModelAssistantMessage(
            content=None,
            tool_calls=[fn_call],
        )
        tool_msg = LanguageModelToolMessage(
            content="The current ECB rate is 4.25%",
            tool_call_id="tc-42",
            name="search_knowledge_base",
        )
        final_assistant = LanguageModelAssistantMessage(
            content="Based on the search, ECB rate is 4.25%."
        )
        messages = [
            _user("What are current interest rates?"),
            intermediate_assistant,
            tool_msg,
            final_assistant,
        ]
        result = format_history_as_text(messages, max_interactions=4)

        assert "[Tool: search_knowledge_base(" in result
        assert 'search_query="ECB rate 2026"' in result
        assert "The current ECB rate is 4.25%" in result

    def test_format_history_truncates_tool_result_content(self) -> None:
        """Tool result content longer than 200 chars is truncated with '...'."""
        long_result = "x" * 300
        tool_msg = LanguageModelToolMessage(
            content=long_result,
            tool_call_id="tc-1",
            name="search",
        )
        messages = [_user("search something"), tool_msg, _assistant("Done.")]
        result = format_history_as_text(messages, max_interactions=4)

        assert long_result not in result
        assert "..." in result

    def test_format_history_tool_message_degrades_gracefully_without_name(
        self,
    ) -> None:
        """Renders '[Tool]' without raising when tool name cannot be matched."""
        tool_msg = LanguageModelToolMessage(
            content="some result",
            tool_call_id="unknown-id",
            name="",
        )
        messages = [_user("query"), tool_msg, _assistant("reply")]
        result = format_history_as_text(messages, max_interactions=4)

        assert "[Tool]" in result
        assert "some result" in result
