"""Unit tests for display module, focusing on HTML formatting and regex removal logic."""

import re

import pytest

from unique_toolkit.agentic.tools.a2a.postprocessing._display import (
    _add_line_break,
    _build_sub_agent_answer_display,
    _get_display_removal_re,
    _get_display_template,
    _join_html_blocks,
    _remove_sub_agent_answer_from_text,
    _wrap_hidden_div,
    _wrap_strong,
    _wrap_with_block_border,
    _wrap_with_details_tag,
    _wrap_with_html_block,
    _wrap_with_quote_border,
)
from unique_toolkit.agentic.tools.a2a.postprocessing.config import (
    SubAgentResponseDisplayMode,
)

# Test _wrap_with_html_block


@pytest.mark.ai
def test_wrap_with_html_block__wraps_text__with_start_and_end_tags() -> None:
    """
    Purpose: Verify text is wrapped with opening and closing tags with proper newlines.
    Why this matters: Foundation for all HTML wrapping operations.
    Setup summary: Provide text and tags, assert formatted output.
    """
    # Arrange
    text = "Hello World"
    start_tag = "<div>"
    end_tag = "</div>"

    # Act
    result = _wrap_with_html_block(text, start_tag, end_tag)

    # Assert
    assert result == "<div>\nHello World\n</div>"


@pytest.mark.ai
def test_wrap_with_html_block__strips_whitespace__from_text_and_tags() -> None:
    """
    Purpose: Ensure whitespace is trimmed from text and tags before wrapping.
    Why this matters: Prevents inconsistent HTML formatting.
    Setup summary: Provide text with whitespace, assert trimmed output.
    """
    # Arrange
    text = "  Hello World  "
    start_tag = "  <div>  "
    end_tag = "  </div>  "

    # Act
    result = _wrap_with_html_block(text, start_tag, end_tag)

    # Assert
    assert result == "<div>\nHello World\n</div>"


@pytest.mark.ai
def test_wrap_with_html_block__handles_empty_tags__no_newlines() -> None:
    """
    Purpose: Verify empty tags don't add newlines to output.
    Why this matters: Allows flexible HTML composition without unwanted whitespace.
    Setup summary: Provide empty tags, assert text without extra newlines.
    """
    # Arrange
    text = "Hello World"
    start_tag = ""
    end_tag = ""

    # Act
    result = _wrap_with_html_block(text, start_tag, end_tag)

    # Assert
    assert result == "Hello World"


@pytest.mark.ai
def test_wrap_with_html_block__handles_mixed_empty_tags__partial_newlines() -> None:
    """
    Purpose: Verify behavior with one empty tag and one non-empty tag.
    Why this matters: Ensures consistent formatting in edge cases.
    Setup summary: Provide start tag only, assert newline only after start.
    """
    # Arrange
    text = "Hello World"
    start_tag = "<div>"
    end_tag = ""

    # Act
    result = _wrap_with_html_block(text, start_tag, end_tag)

    # Assert
    assert result == "<div>\nHello World"


# Test _join_html_blocks


@pytest.mark.ai
def test_join_html_blocks__joins_multiple_blocks__with_newlines() -> None:
    """
    Purpose: Verify multiple HTML blocks are joined with newline separators.
    Why this matters: Creates properly formatted multi-line HTML output.
    Setup summary: Provide multiple blocks, assert newline-joined output.
    """
    # Arrange
    block1 = "<div>Block 1</div>"
    block2 = "<div>Block 2</div>"
    block3 = "<div>Block 3</div>"

    # Act
    result = _join_html_blocks(block1, block2, block3)

    # Assert
    assert result == "<div>Block 1</div>\n<div>Block 2</div>\n<div>Block 3</div>"


@pytest.mark.ai
def test_join_html_blocks__strips_whitespace__from_each_block() -> None:
    """
    Purpose: Ensure whitespace is trimmed from each block before joining.
    Why this matters: Prevents unwanted whitespace in combined HTML.
    Setup summary: Provide blocks with whitespace, assert trimmed joined output.
    """
    # Arrange
    block1 = "  <div>Block 1</div>  "
    block2 = "  <div>Block 2</div>  "

    # Act
    result = _join_html_blocks(block1, block2)

    # Assert
    assert result == "<div>Block 1</div>\n<div>Block 2</div>"


@pytest.mark.ai
def test_join_html_blocks__handles_single_block__no_extra_newlines() -> None:
    """
    Purpose: Verify single block is returned without modification.
    Why this matters: Edge case handling for variable block counts.
    Setup summary: Provide single block, assert unchanged output.
    """
    # Arrange
    block = "<div>Single Block</div>"

    # Act
    result = _join_html_blocks(block)

    # Assert
    assert result == "<div>Single Block</div>"


# Test _wrap_with_details_tag


@pytest.mark.ai
def test_wrap_with_details_tag__wraps_open__without_summary() -> None:
    """
    Purpose: Verify open details tag wrapping without summary element.
    Why this matters: Creates collapsible HTML sections in open state.
    Setup summary: Provide text and open mode, assert details open tag.
    """
    # Arrange
    text = "Content here"

    # Act
    result = _wrap_with_details_tag(text, mode="open", summary_name=None)

    # Assert
    assert result == "<details open>\nContent here\n</details>"


@pytest.mark.ai
def test_wrap_with_details_tag__wraps_closed__without_summary() -> None:
    """
    Purpose: Verify closed details tag wrapping without summary element.
    Why this matters: Creates collapsible HTML sections in closed state.
    Setup summary: Provide text and closed mode, assert details tag.
    """
    # Arrange
    text = "Content here"

    # Act
    result = _wrap_with_details_tag(text, mode="closed", summary_name=None)

    # Assert
    assert result == "<details>\nContent here\n</details>"


@pytest.mark.ai
def test_wrap_with_details_tag__includes_summary__when_provided() -> None:
    """
    Purpose: Verify summary element is added when summary_name provided.
    Why this matters: Creates labeled collapsible sections.
    Setup summary: Provide summary_name, assert summary tag before content.
    """
    # Arrange
    text = "Content here"
    summary_name = "Click to expand"

    # Act
    result = _wrap_with_details_tag(text, mode="closed", summary_name=summary_name)

    # Assert
    expected = "<details>\n<summary>\nClick to expand\n</summary>\nContent here\n</details>"
    assert result == expected


# Test border and style wrappers


@pytest.mark.ai
def test_wrap_with_block_border__adds_styled_div__with_border() -> None:
    """
    Purpose: Verify block border wrapper adds div with border styling.
    Why this matters: Visual separation of content blocks.
    Setup summary: Provide text, assert div with border style.
    """
    # Arrange
    text = "Bordered content"

    # Act
    result = _wrap_with_block_border(text)

    # Assert
    assert result.startswith("<div style='overflow-y: auto; border: 1px solid #ccc;")
    assert "Bordered content" in result
    assert result.endswith("\n</div>")


@pytest.mark.ai
def test_wrap_with_quote_border__adds_styled_div__with_left_border() -> None:
    """
    Purpose: Verify quote border wrapper adds div with left border styling.
    Why this matters: Visual indication of quoted content.
    Setup summary: Provide text, assert div with left border style.
    """
    # Arrange
    text = "Quoted content"

    # Act
    result = _wrap_with_quote_border(text)

    # Assert
    assert result.startswith("<div style='margin-left: 20px; border-left: 2px solid #ccc;")
    assert "Quoted content" in result
    assert result.endswith("\n</div>")


@pytest.mark.ai
def test_wrap_strong__wraps_text__with_strong_tags() -> None:
    """
    Purpose: Verify text is wrapped with strong tags for bold formatting.
    Why this matters: Text emphasis in HTML output.
    Setup summary: Provide text, assert strong tag wrapping.
    """
    # Arrange
    text = "Bold text"

    # Act
    result = _wrap_strong(text)

    # Assert
    assert result == "<strong>\nBold text\n</strong>"


@pytest.mark.ai
def test_wrap_hidden_div__wraps_text__with_display_none() -> None:
    """
    Purpose: Verify text is wrapped in hidden div with display:none style.
    Why this matters: Hides content from visual display while keeping it in DOM.
    Setup summary: Provide text, assert div with display:none.
    """
    # Arrange
    text = "Hidden content"

    # Act
    result = _wrap_hidden_div(text)

    # Assert
    assert result == '<div style="display: none;">\nHidden content\n</div>'


# Test _add_line_break


@pytest.mark.ai
def test_add_line_break__adds_both__by_default() -> None:
    """
    Purpose: Verify line breaks are added before and after text by default.
    Why this matters: Default spacing behavior for content.
    Setup summary: Provide text with defaults, assert br tags both sides.
    """
    # Arrange
    text = "Text content"

    # Act
    result = _add_line_break(text)

    # Assert
    assert result == "<br>\nText content\n<br>"


@pytest.mark.ai
def test_add_line_break__adds_only_before__when_after_false() -> None:
    """
    Purpose: Verify line break only before text when after=False.
    Why this matters: Flexible spacing control.
    Setup summary: Set after=False, assert br only before.
    """
    # Arrange
    text = "Text content"

    # Act
    result = _add_line_break(text, before=True, after=False)

    # Assert
    assert result == "<br>\nText content"


@pytest.mark.ai
def test_add_line_break__adds_only_after__when_before_false() -> None:
    """
    Purpose: Verify line break only after text when before=False.
    Why this matters: Flexible spacing control.
    Setup summary: Set before=False, assert br only after.
    """
    # Arrange
    text = "Text content"

    # Act
    result = _add_line_break(text, before=False, after=True)

    # Assert
    assert result == "Text content\n<br>"


@pytest.mark.ai
def test_add_line_break__adds_none__when_both_false() -> None:
    """
    Purpose: Verify no line breaks added when both flags false.
    Why this matters: Complete control over spacing.
    Setup summary: Set both flags false, assert no br tags.
    """
    # Arrange
    text = "Text content"

    # Act
    result = _add_line_break(text, before=False, after=False)

    # Assert
    assert result == "Text content"


# Test _get_display_template


@pytest.mark.ai
def test_get_display_template__returns_empty__when_hidden_mode() -> None:
    """
    Purpose: Verify empty string returned for HIDDEN display mode.
    Why this matters: Content should not be displayed when hidden.
    Setup summary: Set mode to HIDDEN, assert empty string.
    """
    # Arrange
    mode = SubAgentResponseDisplayMode.HIDDEN

    # Act
    result = _get_display_template(
        mode=mode, add_quote_border=False, add_block_border=False
    )

    # Assert
    assert result == ""


@pytest.mark.ai
def test_get_display_template__includes_placeholders__for_all_modes() -> None:
    """
    Purpose: Verify all required placeholders present in non-hidden modes.
    Why this matters: Template must support variable substitution.
    Setup summary: Test each display mode, assert placeholders exist.
    """
    # Arrange
    modes = [
        SubAgentResponseDisplayMode.PLAIN,
        SubAgentResponseDisplayMode.DETAILS_OPEN,
        SubAgentResponseDisplayMode.DETAILS_CLOSED,
    ]

    for mode in modes:
        # Act
        result = _get_display_template(
            mode=mode, add_quote_border=False, add_block_border=False
        )

        # Assert
        assert "{assistant_id}" in result, f"assistant_id missing in {mode}"
        assert "{answer}" in result, f"answer missing in {mode}"
        assert "{display_name}" in result, f"display_name missing in {mode}"


@pytest.mark.ai
def test_get_display_template__wraps_assistant_id__as_hidden_div() -> None:
    """
    Purpose: Verify assistant_id is always wrapped in hidden div.
    Why this matters: Assistant ID should not be visible to users.
    Setup summary: Check template contains hidden div with assistant_id.
    """
    # Arrange
    mode = SubAgentResponseDisplayMode.PLAIN

    # Act
    result = _get_display_template(
        mode=mode, add_quote_border=False, add_block_border=False
    )

    # Assert
    assert '<div style="display: none;">' in result
    assert "{assistant_id}" in result


@pytest.mark.ai
def test_get_display_template__wraps_display_name__as_strong() -> None:
    """
    Purpose: Verify display_name is wrapped in strong tags for emphasis.
    Why this matters: Display name should be bold for visibility.
    Setup summary: Check template contains strong tags with display_name.
    """
    # Arrange
    mode = SubAgentResponseDisplayMode.PLAIN

    # Act
    result = _get_display_template(
        mode=mode, add_quote_border=False, add_block_border=False
    )

    # Assert
    assert "<strong>" in result
    assert "{display_name}" in result
    assert "</strong>" in result


@pytest.mark.ai
def test_get_display_template__adds_details_open__when_details_open_mode() -> None:
    """
    Purpose: Verify details open tags present in DETAILS_OPEN mode.
    Why this matters: Creates expandable section in open state.
    Setup summary: Set DETAILS_OPEN mode, assert details open tags.
    """
    # Arrange
    mode = SubAgentResponseDisplayMode.DETAILS_OPEN

    # Act
    result = _get_display_template(
        mode=mode, add_quote_border=False, add_block_border=False
    )

    # Assert
    assert "<details open>" in result
    assert "</details>" in result
    assert "<summary>" in result
    assert "</summary>" in result


@pytest.mark.ai
def test_get_display_template__adds_details_closed__when_details_closed_mode() -> None:
    """
    Purpose: Verify details tags present without open in DETAILS_CLOSED mode.
    Why this matters: Creates expandable section in closed state.
    Setup summary: Set DETAILS_CLOSED mode, assert details tags without open.
    """
    # Arrange
    mode = SubAgentResponseDisplayMode.DETAILS_CLOSED

    # Act
    result = _get_display_template(
        mode=mode, add_quote_border=False, add_block_border=False
    )

    # Assert
    assert "<details>" in result
    assert "<details open>" not in result
    assert "</details>" in result
    assert "<summary>" in result
    assert "</summary>" in result


@pytest.mark.ai
def test_get_display_template__adds_line_break_after_name__in_plain_mode() -> None:
    """
    Purpose: Verify line break added after display name in PLAIN mode.
    Why this matters: Separates display name from content visually.
    Setup summary: Set PLAIN mode, assert br tag after display_name.
    """
    # Arrange
    mode = SubAgentResponseDisplayMode.PLAIN

    # Act
    result = _get_display_template(
        mode=mode, add_quote_border=False, add_block_border=False
    )

    # Assert
    # The display_name should be wrapped with line break (before=False, after=True)
    assert "<br>" in result


@pytest.mark.ai
def test_get_display_template__adds_quote_border__when_flag_true() -> None:
    """
    Purpose: Verify quote border styling added when add_quote_border=True.
    Why this matters: Visual indication of quoted content.
    Setup summary: Set add_quote_border=True, assert quote border style.
    """
    # Arrange
    mode = SubAgentResponseDisplayMode.PLAIN

    # Act
    result = _get_display_template(
        mode=mode, add_quote_border=True, add_block_border=False
    )

    # Assert
    assert "margin-left: 20px" in result
    assert "border-left: 2px solid #ccc" in result


@pytest.mark.ai
def test_get_display_template__adds_block_border__when_flag_true() -> None:
    """
    Purpose: Verify block border styling added when add_block_border=True.
    Why this matters: Visual separation of content blocks.
    Setup summary: Set add_block_border=True, assert block border style.
    """
    # Arrange
    mode = SubAgentResponseDisplayMode.PLAIN

    # Act
    result = _get_display_template(
        mode=mode, add_quote_border=False, add_block_border=True
    )

    # Assert
    assert "overflow-y: auto" in result
    assert "border: 1px solid #ccc" in result


@pytest.mark.ai
def test_get_display_template__adds_both_borders__when_both_flags_true() -> None:
    """
    Purpose: Verify both border styles added when both flags true.
    Why this matters: Support for combining visual styles.
    Setup summary: Set both border flags true, assert both styles present.
    """
    # Arrange
    mode = SubAgentResponseDisplayMode.PLAIN

    # Act
    result = _get_display_template(
        mode=mode, add_quote_border=True, add_block_border=True
    )

    # Assert
    # Quote border should be inside block border
    assert "overflow-y: auto" in result
    assert "border: 1px solid #ccc" in result
    assert "margin-left: 20px" in result
    assert "border-left: 2px solid #ccc" in result


# Test _get_display_removal_re (regex pattern generation)


@pytest.mark.ai
def test_get_display_removal_re__returns_pattern__for_plain_mode() -> None:
    """
    Purpose: Verify regex pattern is created for PLAIN display mode.
    Why this matters: Enables removal of displayed content from text.
    Setup summary: Generate pattern for PLAIN mode, assert Pattern type.
    """
    # Arrange
    assistant_id = "test-assistant-123"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Act
    result = _get_display_removal_re(
        assistant_id=assistant_id,
        mode=mode,
        add_quote_border=False,
        add_block_border=False,
    )

    # Assert
    assert isinstance(result, re.Pattern)
    assert result.flags & re.DOTALL  # Should have DOTALL flag


@pytest.mark.ai
def test_get_display_removal_re__returns_pattern__for_details_modes() -> None:
    """
    Purpose: Verify regex patterns created for both DETAILS modes.
    Why this matters: Ensures removal works for collapsible sections.
    Setup summary: Generate patterns for DETAILS modes, assert Pattern types.
    """
    # Arrange
    assistant_id = "test-assistant-123"
    modes = [
        SubAgentResponseDisplayMode.DETAILS_OPEN,
        SubAgentResponseDisplayMode.DETAILS_CLOSED,
    ]

    for mode in modes:
        # Act
        result = _get_display_removal_re(
            assistant_id=assistant_id,
            mode=mode,
            add_quote_border=False,
            add_block_border=False,
        )

        # Assert
        assert isinstance(result, re.Pattern), f"Pattern not created for {mode}"
        assert result.flags & re.DOTALL, f"DOTALL flag missing for {mode}"


@pytest.mark.ai
def test_get_display_removal_re__includes_assistant_id__in_pattern() -> None:
    """
    Purpose: Verify assistant_id is embedded in regex pattern.
    Why this matters: Ensures only specific assistant's content is removed.
    Setup summary: Generate pattern with assistant_id, assert ID in pattern.
    """
    # Arrange
    assistant_id = "unique-assistant-xyz"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Act
    result = _get_display_removal_re(
        assistant_id=assistant_id,
        mode=mode,
        add_quote_border=False,
        add_block_border=False,
    )

    # Assert
    assert assistant_id in result.pattern


@pytest.mark.ai
def test_get_display_removal_re__has_capture_groups__for_answer_and_name() -> None:
    """
    Purpose: Verify regex pattern includes capture groups for dynamic content.
    Why this matters: Allows flexible matching of variable content.
    Setup summary: Check pattern contains regex capture groups.
    """
    # Arrange
    assistant_id = "test-assistant"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Act
    result = _get_display_removal_re(
        assistant_id=assistant_id,
        mode=mode,
        add_quote_border=False,
        add_block_border=False,
    )

    # Assert
    # Pattern should contain (.*?) for capturing groups
    assert "(.*?)" in result.pattern


# Test _build_sub_agent_answer_display


@pytest.mark.ai
def test_build_sub_agent_answer_display__creates_html__for_plain_mode() -> None:
    """
    Purpose: Verify HTML output is generated for PLAIN display mode.
    Why this matters: Core functionality for displaying agent responses.
    Setup summary: Build display with PLAIN mode, assert HTML structure.
    """
    # Arrange
    display_name = "Test Agent"
    answer = "This is the answer"
    assistant_id = "agent-123"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Act
    result = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    # Assert
    assert "Test Agent" in result
    assert "This is the answer" in result
    assert "agent-123" in result
    assert '<div style="display: none;">' in result
    assert "<strong>" in result


@pytest.mark.ai
def test_build_sub_agent_answer_display__creates_details__for_details_open() -> None:
    """
    Purpose: Verify details HTML with open attribute for DETAILS_OPEN mode.
    Why this matters: Creates expandable sections in open state.
    Setup summary: Build display with DETAILS_OPEN, assert details open tags.
    """
    # Arrange
    display_name = "Test Agent"
    answer = "This is the answer"
    assistant_id = "agent-123"
    mode = SubAgentResponseDisplayMode.DETAILS_OPEN

    # Act
    result = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    # Assert
    assert "<details open>" in result
    assert "</details>" in result
    assert "<summary>" in result
    assert "Test Agent" in result
    assert "This is the answer" in result


@pytest.mark.ai
def test_build_sub_agent_answer_display__creates_details__for_details_closed() -> None:
    """
    Purpose: Verify details HTML without open for DETAILS_CLOSED mode.
    Why this matters: Creates expandable sections in closed state.
    Setup summary: Build display with DETAILS_CLOSED, assert details tags.
    """
    # Arrange
    display_name = "Test Agent"
    answer = "This is the answer"
    assistant_id = "agent-123"
    mode = SubAgentResponseDisplayMode.DETAILS_CLOSED

    # Act
    result = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    # Assert
    assert "<details>" in result
    assert "<details open>" not in result
    assert "</details>" in result
    assert "<summary>" in result
    assert "Test Agent" in result


@pytest.mark.ai
def test_build_sub_agent_answer_display__returns_empty__for_hidden_mode() -> None:
    """
    Purpose: Verify empty string returned for HIDDEN display mode.
    Why this matters: Hidden content should not generate any HTML.
    Setup summary: Build display with HIDDEN mode, assert empty string.
    """
    # Arrange
    display_name = "Test Agent"
    answer = "This is the answer"
    assistant_id = "agent-123"
    mode = SubAgentResponseDisplayMode.HIDDEN

    # Act
    result = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    # Assert
    assert result == ""


# Test _remove_sub_agent_answer_from_text (regex removal logic)


@pytest.mark.ai
def test_remove_sub_agent_answer__removes_plain_display__from_text() -> None:
    """
    Purpose: Verify PLAIN mode display content is removed from text via regex.
    Why this matters: Core removal functionality for cleaning history.
    Setup summary: Build display, embed in text, remove via regex, assert removal.
    """
    # Arrange
    assistant_id = "agent-123"
    display_name = "Test Agent"
    answer = "This is the answer"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Build the display
    display = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    text_with_display = f"Before content\n{display}\nAfter content"

    # Act
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        text=text_with_display,
        assistant_id=assistant_id,
    )

    # Assert
    assert "This is the answer" not in result
    assert "Test Agent" not in result
    assert "Before content" in result
    assert "After content" in result


@pytest.mark.ai
def test_remove_sub_agent_answer__removes_details_open__from_text() -> None:
    """
    Purpose: Verify DETAILS_OPEN mode display is removed via regex.
    Why this matters: Ensures removal works for collapsible open sections.
    Setup summary: Build details open display, embed and remove, assert removal.
    """
    # Arrange
    assistant_id = "agent-456"
    display_name = "Research Agent"
    answer = "Research findings here"
    mode = SubAgentResponseDisplayMode.DETAILS_OPEN

    # Build the display
    display = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    text_with_display = f"Start\n{display}\nEnd"

    # Act
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        text=text_with_display,
        assistant_id=assistant_id,
    )

    # Assert
    assert "Research findings here" not in result
    assert "Research Agent" not in result
    assert "<details open>" not in result
    assert "Start" in result
    assert "End" in result


@pytest.mark.ai
def test_remove_sub_agent_answer__removes_details_closed__from_text() -> None:
    """
    Purpose: Verify DETAILS_CLOSED mode display is removed via regex.
    Why this matters: Ensures removal works for collapsible closed sections.
    Setup summary: Build details closed display, embed and remove, assert removal.
    """
    # Arrange
    assistant_id = "agent-789"
    display_name = "Analysis Agent"
    answer = "Analysis results"
    mode = SubAgentResponseDisplayMode.DETAILS_CLOSED

    # Build the display
    display = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    text_with_display = f"Beginning\n{display}\nEnding"

    # Act
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        text=text_with_display,
        assistant_id=assistant_id,
    )

    # Assert
    assert "Analysis results" not in result
    assert "Analysis Agent" not in result
    assert "<details>" not in result
    assert "Beginning" in result
    assert "Ending" in result


@pytest.mark.ai
def test_remove_sub_agent_answer__removes_with_quote_border__from_text() -> None:
    """
    Purpose: Verify removal works when quote border styling is present.
    Why this matters: Regex must handle additional div wrapper.
    Setup summary: Build display with quote border, remove, assert successful removal.
    """
    # Arrange
    assistant_id = "agent-quote"
    display_name = "Quote Agent"
    answer = "Quoted answer"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Build with quote border
    display = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=True,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    text_with_display = f"Before\n{display}\nAfter"

    # Act
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=True,
        add_block_border=False,
        text=text_with_display,
        assistant_id=assistant_id,
    )

    # Assert
    assert "Quoted answer" not in result
    assert "Quote Agent" not in result
    assert "margin-left: 20px" not in result
    assert "Before" in result
    assert "After" in result


@pytest.mark.ai
def test_remove_sub_agent_answer__removes_with_block_border__from_text() -> None:
    """
    Purpose: Verify removal works when block border styling is present.
    Why this matters: Regex must handle block border div wrapper.
    Setup summary: Build display with block border, remove, assert successful removal.
    """
    # Arrange
    assistant_id = "agent-block"
    display_name = "Block Agent"
    answer = "Block answer"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Build with block border
    display = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=True,
        answer=answer,
        assistant_id=assistant_id,
    )

    text_with_display = f"Start\n{display}\nFinish"

    # Act
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=False,
        add_block_border=True,
        text=text_with_display,
        assistant_id=assistant_id,
    )

    # Assert
    assert "Block answer" not in result
    assert "Block Agent" not in result
    assert "overflow-y: auto" not in result
    assert "Start" in result
    assert "Finish" in result


@pytest.mark.ai
def test_remove_sub_agent_answer__removes_with_both_borders__from_text() -> None:
    """
    Purpose: Verify removal works with both quote and block borders.
    Why this matters: Regex must handle nested div wrappers.
    Setup summary: Build display with both borders, remove, assert successful removal.
    """
    # Arrange
    assistant_id = "agent-both"
    display_name = "Both Borders Agent"
    answer = "Answer with borders"
    mode = SubAgentResponseDisplayMode.DETAILS_OPEN

    # Build with both borders
    display = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=True,
        add_block_border=True,
        answer=answer,
        assistant_id=assistant_id,
    )

    text_with_display = f"Prefix\n{display}\nSuffix"

    # Act
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=True,
        add_block_border=True,
        text=text_with_display,
        assistant_id=assistant_id,
    )

    # Assert
    assert "Answer with borders" not in result
    assert "Both Borders Agent" not in result
    assert "<details open>" not in result
    assert "Prefix" in result
    assert "Suffix" in result


@pytest.mark.ai
def test_remove_sub_agent_answer__preserves_other_content__with_multiple_displays() -> None:
    """
    Purpose: Verify removal only affects specified assistant_id.
    Why this matters: Must not remove content from different assistants.
    Setup summary: Embed multiple assistants, remove one, assert selective removal.
    """
    # Arrange
    assistant_id_1 = "agent-1"
    assistant_id_2 = "agent-2"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Build displays for two different assistants
    display_1 = _build_sub_agent_answer_display(
        display_name="Agent 1",
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer="Answer from agent 1",
        assistant_id=assistant_id_1,
    )

    display_2 = _build_sub_agent_answer_display(
        display_name="Agent 2",
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer="Answer from agent 2",
        assistant_id=assistant_id_2,
    )

    text_with_displays = f"Start\n{display_1}\nMiddle\n{display_2}\nEnd"

    # Act - Remove only agent-1's display
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        text=text_with_displays,
        assistant_id=assistant_id_1,
    )

    # Assert
    assert "Answer from agent 1" not in result  # Removed
    assert "Agent 1" not in result  # Removed
    assert "Answer from agent 2" in result  # Preserved
    assert "Agent 2" in result  # Preserved
    assert "Start" in result
    assert "Middle" in result
    assert "End" in result


@pytest.mark.ai
def test_remove_sub_agent_answer__handles_multiline_answer__with_dotall_flag() -> None:
    """
    Purpose: Verify removal works for multiline answers using DOTALL regex flag.
    Why this matters: Answers can span multiple lines with newlines.
    Setup summary: Build display with multiline answer, remove, assert removal.
    """
    # Arrange
    assistant_id = "agent-multiline"
    display_name = "Multiline Agent"
    answer = "Line 1\nLine 2\nLine 3\nWith many\nnewlines"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Build the display
    display = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    text_with_display = f"Before\n{display}\nAfter"

    # Act
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        text=text_with_display,
        assistant_id=assistant_id,
    )

    # Assert
    assert "Line 1" not in result
    assert "Line 2" not in result
    assert "Line 3" not in result
    assert "With many" not in result
    assert "Multiline Agent" not in result
    assert "Before" in result
    assert "After" in result


@pytest.mark.ai
def test_remove_sub_agent_answer__handles_special_regex_chars__in_answer() -> None:
    """
    Purpose: Verify removal works when answer contains regex special characters.
    Why this matters: Template uses (.*?) which should match any content safely.
    Setup summary: Build display with regex chars in answer, remove, assert removal.
    """
    # Arrange
    assistant_id = "agent-special"
    display_name = "Special Chars"
    answer = "Answer with $pecial ch@rs: .* + ? [ ] { } ( ) | \\"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Build the display
    display = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    text_with_display = f"Start\n{display}\nEnd"

    # Act
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        text=text_with_display,
        assistant_id=assistant_id,
    )

    # Assert
    assert "$pecial ch@rs" not in result
    assert "Special Chars" not in result
    assert "Start" in result
    assert "End" in result


@pytest.mark.ai
def test_remove_sub_agent_answer__handles_empty_answer__successfully() -> None:
    """
    Purpose: Verify removal works when answer is empty string.
    Why this matters: Edge case handling for empty content.
    Setup summary: Build display with empty answer, remove, assert removal.
    """
    # Arrange
    assistant_id = "agent-empty"
    display_name = "Empty Answer Agent"
    answer = ""
    mode = SubAgentResponseDisplayMode.PLAIN

    # Build the display
    display = _build_sub_agent_answer_display(
        display_name=display_name,
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer=answer,
        assistant_id=assistant_id,
    )

    text_with_display = f"Beginning\n{display}\nEnding"

    # Act
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        text=text_with_display,
        assistant_id=assistant_id,
    )

    # Assert
    assert "Empty Answer Agent" not in result
    assert "Beginning" in result
    assert "Ending" in result


@pytest.mark.ai
def test_remove_sub_agent_answer__no_op_when_assistant_not_found() -> None:
    """
    Purpose: Verify text unchanged when assistant_id has no matching display.
    Why this matters: Should not modify text when target not present.
    Setup summary: Build display for one assistant, try removing different one.
    """
    # Arrange
    assistant_id_present = "agent-present"
    assistant_id_absent = "agent-absent"
    mode = SubAgentResponseDisplayMode.PLAIN

    # Build display for present assistant
    display = _build_sub_agent_answer_display(
        display_name="Present Agent",
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        answer="Present answer",
        assistant_id=assistant_id_present,
    )

    text_with_display = f"Start\n{display}\nEnd"
    original_text = text_with_display

    # Act - Try to remove absent assistant
    result = _remove_sub_agent_answer_from_text(
        display_mode=mode,
        add_quote_border=False,
        add_block_border=False,
        text=text_with_display,
        assistant_id=assistant_id_absent,
    )

    # Assert
    assert result == original_text
    assert "Present answer" in result
    assert "Present Agent" in result

