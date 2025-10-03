import re

import pytest

from unique_toolkit.agentic.tools.a2a.postprocessing._display import (
    _build_sub_agent_answer_display,
    _DetailsResponseDisplayHandler,
    _remove_sub_agent_answer_from_text,
)
from unique_toolkit.agentic.tools.a2a.postprocessing.config import (
    SubAgentResponseDisplayMode,
)


class TestDetailsResponseDisplayHandler:
    """Test suite for DetailsResponseDisplayHandler class."""

    @pytest.fixture
    def open_handler(self) -> _DetailsResponseDisplayHandler:
        """Create a handler with open mode."""
        return _DetailsResponseDisplayHandler(mode="open")

    @pytest.fixture
    def closed_handler(self) -> _DetailsResponseDisplayHandler:
        """Create a handler with closed mode."""
        return _DetailsResponseDisplayHandler(mode="closed")

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {
            "display_name": "Test Assistant",
            "assistant_id": "test_assistant_123",
            "answer": "This is a test answer with multiple lines.\nSecond line here.",
        }

    def test_build_response_display_open_mode(self, open_handler, sample_data):
        """Test building response display in open mode."""
        result = open_handler.build_response_display(
            display_name=sample_data["display_name"],
            assistant_id=sample_data["assistant_id"],
            answer=sample_data["answer"],
        )

        assert "<details open>" in result
        assert (
            f'<div style="display: none;">{sample_data["assistant_id"]}</div>' in result
        )
        assert f"<summary>{sample_data['display_name']}</summary>" in result
        assert sample_data["answer"] in result
        assert "</details>" in result

    def test_build_response_display_closed_mode(self, closed_handler, sample_data):
        """Test building response display in closed mode."""
        result = closed_handler.build_response_display(
            display_name=sample_data["display_name"],
            assistant_id=sample_data["assistant_id"],
            answer=sample_data["answer"],
        )

        assert "<details>" in result
        assert "<details open>" not in result
        assert (
            f'<div style="display: none;">{sample_data["assistant_id"]}</div>' in result
        )
        assert f"<summary>{sample_data['display_name']}</summary>" in result
        assert sample_data["answer"] in result
        assert "</details>" in result

    def test_build_response_display_with_special_characters(self, open_handler):
        """Test building response display with special characters in content."""
        result = open_handler.build_response_display(
            display_name="Test & Co.",
            assistant_id="test<>123",
            answer="Answer with <tags> & symbols",
        )

        assert "Test & Co." in result
        assert "test<>123" in result
        assert "Answer with <tags> & symbols" in result

    def test_remove_response_display_open_mode(self, open_handler, sample_data):
        """Test removing response display from text in open mode."""
        # First build the display
        display_html = open_handler.build_response_display(
            display_name=sample_data["display_name"],
            assistant_id=sample_data["assistant_id"],
            answer=sample_data["answer"],
        )

        # Create text with the display embedded
        text_with_display = f"Some text before\n{display_html}\nSome text after"

        # Remove the display
        result = open_handler.remove_response_display(
            assistant_id=sample_data["assistant_id"], text=text_with_display
        )

        assert "Some text before" in result
        assert "Some text after" in result
        assert sample_data["display_name"] not in result
        assert sample_data["answer"] not in result

    def test_remove_response_display_closed_mode(self, closed_handler, sample_data):
        """Test removing response display from text in closed mode."""
        # First build the display
        display_html = closed_handler.build_response_display(
            display_name=sample_data["display_name"],
            assistant_id=sample_data["assistant_id"],
            answer=sample_data["answer"],
        )

        # Create text with the display embedded
        text_with_display = f"Some text before\n{display_html}\nSome text after"

        # Remove the display
        result = closed_handler.remove_response_display(
            assistant_id=sample_data["assistant_id"], text=text_with_display
        )

        assert "Some text before" in result
        assert "Some text after" in result
        assert sample_data["display_name"] not in result
        assert sample_data["answer"] not in result

    def test_remove_response_display_multiple_instances(self, open_handler):
        """Test removing multiple instances of response display."""
        assistant_id = "test_123"

        display1 = open_handler.build_response_display(
            display_name="First", assistant_id=assistant_id, answer="First answer"
        )

        display2 = open_handler.build_response_display(
            display_name="Second", assistant_id=assistant_id, answer="Second answer"
        )

        text_with_displays = f"Start\n{display1}\nMiddle\n{display2}\nEnd"

        result = open_handler.remove_response_display(
            assistant_id=assistant_id, text=text_with_displays
        )

        assert "Start" in result
        assert "Middle" in result
        assert "End" in result
        assert "First answer" not in result
        assert "Second answer" not in result

    def test_remove_response_display_no_match(self, open_handler):
        """Test removing response display when no match exists."""
        text = "This is some text without any displays"
        result = open_handler.remove_response_display(
            assistant_id="nonexistent", text=text
        )
        assert result == text

    def test_remove_response_display_with_regex_special_chars(self, open_handler):
        """Test removing response display with regex special characters in assistant_id."""
        assistant_id = "test.+*?[]{}()^$|"

        display_html = open_handler.build_response_display(
            display_name="Test", assistant_id=assistant_id, answer="Test answer"
        )

        text_with_display = f"Before\n{display_html}\nAfter"

        result = open_handler.remove_response_display(
            assistant_id=assistant_id, text=text_with_display
        )

        assert "Before" in result
        assert "After" in result
        assert "Test answer" not in result

    def test_get_detect_re_pattern_validity(self, open_handler, closed_handler):
        """Test that the regex patterns are valid and compilable."""
        assistant_id = "test_123"

        open_pattern = open_handler._get_detect_re(assistant_id)
        closed_pattern = closed_handler._get_detect_re(assistant_id)

        # Should not raise exceptions
        re.compile(open_pattern)
        re.compile(closed_pattern)

        assert "(?s)" in open_pattern  # multiline flag
        assert "(?s)" in closed_pattern
        assert "details open" in open_pattern
        assert "details>" in closed_pattern
        assert "details open" not in closed_pattern


class TestDisplayFunctions:
    """Test suite for module-level display functions."""

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {
            "display_name": "Test Assistant",
            "assistant_id": "test_assistant_123",
            "answer": "This is a test answer.",
        }

    @pytest.mark.parametrize(
        "display_mode,expected_content,not_expected_content",
        [
            (SubAgentResponseDisplayMode.DETAILS_OPEN, "<details open>", None),
            (SubAgentResponseDisplayMode.DETAILS_CLOSED, "<details>", "<details open>"),
            (SubAgentResponseDisplayMode.HIDDEN, "", None),
        ],
    )
    def test_build_sub_agent_answer_display(
        self, sample_data, display_mode, expected_content, not_expected_content
    ):
        """Test building sub-agent answer display with different modes."""
        result = _build_sub_agent_answer_display(
            display_name=sample_data["display_name"],
            display_mode=display_mode,
            answer=sample_data["answer"],
            assistant_id=sample_data["assistant_id"],
        )

        if display_mode == SubAgentResponseDisplayMode.HIDDEN:
            assert result == ""
        else:
            assert expected_content in result
            assert sample_data["display_name"] in result
            assert sample_data["answer"] in result
            assert sample_data["assistant_id"] in result

            if not_expected_content:
                assert not_expected_content not in result

    @pytest.mark.parametrize(
        "display_mode",
        [
            SubAgentResponseDisplayMode.DETAILS_OPEN,
            SubAgentResponseDisplayMode.DETAILS_CLOSED,
        ],
    )
    def test_remove_sub_agent_answer_from_text_details_modes(
        self, sample_data, display_mode
    ):
        """Test removing sub-agent answer from text with DETAILS_OPEN and DETAILS_CLOSED modes."""
        # First build the display
        display_html = _build_sub_agent_answer_display(
            display_name=sample_data["display_name"],
            display_mode=display_mode,
            answer=sample_data["answer"],
            assistant_id=sample_data["assistant_id"],
        )

        text_with_display = f"Before\n{display_html}\nAfter"

        result = _remove_sub_agent_answer_from_text(
            display_mode=display_mode,
            text=text_with_display,
            assistant_id=sample_data["assistant_id"],
        )

        assert "Before" in result
        assert "After" in result
        assert sample_data["answer"] not in result

    def test_remove_sub_agent_answer_from_text_hidden_mode(self, sample_data):
        """Test removing sub-agent answer from text with HIDDEN mode."""
        text = "Some text here"
        result = _remove_sub_agent_answer_from_text(
            display_mode=SubAgentResponseDisplayMode.HIDDEN,
            text=text,
            assistant_id=sample_data["assistant_id"],
        )

        assert result == text

    def test_roundtrip_build_and_remove(self, sample_data):
        """Test that building and then removing display results in clean text."""
        original_text = "This is the original text."

        # Build display
        display_html = _build_sub_agent_answer_display(
            display_name=sample_data["display_name"],
            display_mode=SubAgentResponseDisplayMode.DETAILS_OPEN,
            answer=sample_data["answer"],
            assistant_id=sample_data["assistant_id"],
        )

        # Insert into text
        text_with_display = f"{original_text}\n{display_html}"

        # Remove display
        result = _remove_sub_agent_answer_from_text(
            display_mode=SubAgentResponseDisplayMode.DETAILS_OPEN,
            text=text_with_display,
            assistant_id=sample_data["assistant_id"],
        )

        # Should be back to original (with some whitespace differences)
        assert original_text in result.strip()
        assert sample_data["answer"] not in result


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_empty_strings(self):
        """Test handling of empty strings."""
        handler = _DetailsResponseDisplayHandler(mode="open")

        result = handler.build_response_display(
            display_name="", assistant_id="test", answer=""
        )

        assert "<details open>" in result
        assert "<summary></summary>" in result

    def test_multiline_content(self):
        """Test handling of multiline content."""
        handler = _DetailsResponseDisplayHandler(mode="open")

        multiline_answer = """Line 1
        Line 2
        Line 3 with    spaces
        
        Line 5 after blank line"""

        result = handler.build_response_display(
            display_name="Multi-line Test",
            assistant_id="test_ml",
            answer=multiline_answer,
        )

        assert multiline_answer in result

        # Test removal
        text_with_display = f"Before\n{result}\nAfter"
        clean_result = handler.remove_response_display(
            assistant_id="test_ml", text=text_with_display
        )

        assert "Before" in clean_result
        assert "After" in clean_result
        assert multiline_answer not in clean_result

    def test_html_content_in_answer(self):
        """Test handling of HTML content within the answer."""
        handler = _DetailsResponseDisplayHandler(mode="open")

        html_answer = "<p>This is <strong>bold</strong> text with <em>emphasis</em></p>"

        result = handler.build_response_display(
            display_name="HTML Test", assistant_id="test_html", answer=html_answer
        )

        assert html_answer in result

        # Test removal
        text_with_display = f"Before\n{result}\nAfter"
        clean_result = handler.remove_response_display(
            assistant_id="test_html", text=text_with_display
        )

        assert "Before" in clean_result
        assert "After" in clean_result
        assert html_answer not in clean_result

    def test_unicode_content(self):
        """Test handling of Unicode content."""
        handler = _DetailsResponseDisplayHandler(mode="open")

        unicode_content = "Testing Unicode: 你好 🌟 café naïve résumé"

        result = handler.build_response_display(
            display_name="Unicode Test",
            assistant_id="test_unicode",
            answer=unicode_content,
        )

        assert unicode_content in result

        # Test removal
        text_with_display = f"Before\n{result}\nAfter"
        clean_result = handler.remove_response_display(
            assistant_id="test_unicode", text=text_with_display
        )

        assert "Before" in clean_result
        assert "After" in clean_result
        assert unicode_content not in clean_result
