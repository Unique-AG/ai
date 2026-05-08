"""
Unit tests for utility functions in service.py for SubAgentTool.
"""

import json
import re
from typing import Any

import pytest

from unique_toolkit.agentic.tools.a2a.tool.config import (
    FixedSystemReminderConfig,
    NoReferenceSystemReminderConfig,
    ReferenceSystemReminderConfig,
    RegExpDetectedSystemReminderConfig,
)
from unique_toolkit.agentic.tools.a2a.tool.service import (
    _format_response,
    _get_sub_agent_system_reminders,
    _prepare_sub_agent_response_refs,
    _remove_extra_refs,
    _response_has_refs,
)

# Fixtures


@pytest.fixture
def base_message_response() -> dict[str, Any]:
    """Base message response fixture mimicking unique_sdk.Space.Message."""
    return {
        "text": "Some response text",
        "references": None,
        "chatId": "chat-123",
        "assessment": None,
    }


@pytest.fixture
def message_with_refs() -> dict[str, Any]:
    """Message response with references that appear in text."""
    return {
        "text": "This is the answer <sup>1</sup> and also <sup>2</sup>",
        "references": [
            {"sequenceNumber": 1, "name": "Doc 1", "url": "http://example.com/1"},
            {"sequenceNumber": 2, "name": "Doc 2", "url": "http://example.com/2"},
        ],
        "chatId": "chat-123",
        "assessment": None,
    }


@pytest.fixture
def refs_list() -> list[dict[str, Any]]:
    """List of reference objects mimicking unique_sdk.Space.Reference."""
    return [
        {"sequenceNumber": 1, "name": "Doc 1", "url": "http://example.com/1"},
        {"sequenceNumber": 2, "name": "Doc 2", "url": "http://example.com/2"},
    ]


# Tests for _format_response


@pytest.mark.ai
def test_format_response__returns_text__when_no_system_reminders() -> None:
    """
    Purpose: Verify _format_response returns plain text when system_reminders is empty.
    Why this matters: Avoids unnecessary JSON wrapping for simple responses.
    Setup summary: Empty system_reminders list, assert text returned unchanged.
    """
    # Arrange
    tool_name = "TestTool"
    text = "This is the response text"
    system_reminders: list[str] = []

    # Act
    result = _format_response(tool_name, text, system_reminders)

    # Assert
    assert result == text


@pytest.mark.ai
def test_format_response__returns_json__when_system_reminders_present() -> None:
    """
    Purpose: Verify _format_response returns JSON with reminders when reminders present.
    Why this matters: Ensures system reminders are properly included for LLM context.
    Setup summary: Provide system reminders, assert JSON structure with reminders key.
    """
    # Arrange
    tool_name = "TestTool"
    text = "This is the response"
    system_reminders = ["Remember to cite sources", "Be concise"]

    # Act
    result = _format_response(tool_name, text, system_reminders)

    # Assert
    parsed = json.loads(result)
    assert "TestTool response" in parsed
    assert parsed["TestTool response"] == text
    assert "SYSTEM_REMINDERS" in parsed
    assert parsed["SYSTEM_REMINDERS"] == system_reminders


@pytest.mark.ai
def test_format_response__uses_tool_name_in_key__correctly() -> None:
    """
    Purpose: Verify the response key includes the tool name.
    Why this matters: Allows LLM to identify which tool the response belongs to.
    Setup summary: Use specific tool name, verify it appears in JSON key.
    """
    # Arrange
    tool_name = "MySpecialAgent"
    text = "Response content"
    system_reminders = ["Reminder 1"]

    # Act
    result = _format_response(tool_name, text, system_reminders)

    # Assert
    parsed = json.loads(result)
    assert "MySpecialAgent response" in parsed


@pytest.mark.ai
def test_format_response__preserves_special_characters__in_text() -> None:
    """
    Purpose: Verify special characters in text are preserved in JSON output.
    Why this matters: Ensures markdown, code, and special chars don't break formatting.
    Setup summary: Text with special JSON chars, verify they're properly escaped.
    """
    # Arrange
    tool_name = "TestTool"
    text = 'Text with "quotes" and newlines\nand tabs\t'
    system_reminders = ["Reminder"]

    # Act
    result = _format_response(tool_name, text, system_reminders)

    # Assert
    parsed = json.loads(result)
    assert parsed["TestTool response"] == text


# Tests for _response_has_refs


@pytest.mark.ai
def test_response_has_refs__returns_false__when_text_is_none() -> None:
    """
    Purpose: Verify _response_has_refs returns False when text is None.
    Why this matters: Handles edge case of empty/null responses gracefully.
    Setup summary: Response with None text, assert False returned.
    """
    # Arrange
    response = {"text": None, "references": [{"sequenceNumber": 1}]}

    # Act
    result = _response_has_refs(response)

    # Assert
    assert result is False


@pytest.mark.ai
def test_response_has_refs__returns_false__when_references_is_none() -> None:
    """
    Purpose: Verify _response_has_refs returns False when references is None.
    Why this matters: Handles missing references attribute gracefully.
    Setup summary: Response with None references, assert False returned.
    """
    # Arrange
    response = {"text": "Some text <sup>1</sup>", "references": None}

    # Act
    result = _response_has_refs(response)

    # Assert
    assert result is False


@pytest.mark.ai
def test_response_has_refs__returns_false__when_references_empty() -> None:
    """
    Purpose: Verify _response_has_refs returns False when references list is empty.
    Why this matters: Distinguishes between missing and empty reference lists.
    Setup summary: Response with empty references list, assert False returned.
    """
    # Arrange
    response = {"text": "Some text <sup>1</sup>", "references": []}

    # Act
    result = _response_has_refs(response)

    # Assert
    assert result is False


@pytest.mark.ai
def test_response_has_refs__returns_true__when_ref_found_in_text(
    message_with_refs: dict[str, Any],
) -> None:
    """
    Purpose: Verify _response_has_refs returns True when reference appears in text.
    Why this matters: Core functionality for detecting valid references.
    Setup summary: Response with refs that appear in text, assert True returned.
    """
    # Act
    result = _response_has_refs(message_with_refs)

    # Assert
    assert result is True


@pytest.mark.ai
def test_response_has_refs__returns_false__when_refs_not_in_text() -> None:
    """
    Purpose: Verify _response_has_refs returns False when references don't appear in text.
    Why this matters: Ensures we only process actually-used references.
    Setup summary: Response with refs that don't match text, assert False returned.
    """
    # Arrange
    response = {
        "text": "Text without any sup tags",
        "references": [{"sequenceNumber": 1}, {"sequenceNumber": 2}],
    }

    # Act
    result = _response_has_refs(response)

    # Assert
    assert result is False


@pytest.mark.ai
def test_response_has_refs__handles_whitespace_in_refs__correctly() -> None:
    """
    Purpose: Verify _response_has_refs handles whitespace inside sup tags.
    Why this matters: Reference patterns may have varying whitespace.
    Setup summary: Text with whitespace in sup tags, assert still detected.
    """
    # Arrange
    response = {
        "text": "Text with <sup> 1 </sup> reference",
        "references": [{"sequenceNumber": 1}],
    }

    # Act
    result = _response_has_refs(response)

    # Assert
    assert result is True


@pytest.mark.ai
def test_response_has_refs__returns_true__when_at_least_one_ref_matches() -> None:
    """
    Purpose: Verify returns True if any reference matches, not necessarily all.
    Why this matters: Partial reference usage is still valid.
    Setup summary: Multiple refs where only one appears in text, assert True.
    """
    # Arrange
    response = {
        "text": "Only first ref <sup>1</sup> is used",
        "references": [
            {"sequenceNumber": 1},
            {"sequenceNumber": 2},
            {"sequenceNumber": 3},
        ],
    }

    # Act
    result = _response_has_refs(response)

    # Assert
    assert result is True


# Tests for _remove_extra_refs


@pytest.mark.ai
def test_remove_extra_refs__returns_unchanged__when_no_refs_in_text() -> None:
    """
    Purpose: Verify _remove_extra_refs returns text unchanged when no refs present.
    Why this matters: Avoids unnecessary string manipulation.
    Setup summary: Plain text without refs, assert unchanged.
    """
    # Arrange
    response = "This is plain text without references"
    refs: list[dict[str, Any]] = []

    # Act
    result = _remove_extra_refs(response, refs)

    # Assert
    assert result == response


@pytest.mark.ai
def test_remove_extra_refs__removes_orphan_refs__not_in_refs_list() -> None:
    """
    Purpose: Verify _remove_extra_refs removes refs that aren't in the refs list.
    Why this matters: Cleans up invalid/orphan reference markers.
    Setup summary: Text with refs not in refs list, verify they're removed.
    """
    # Arrange
    response = "Text with <sup>1</sup> and <sup>2</sup> and <sup>3</sup>"
    refs = [{"sequenceNumber": 1}]  # Only ref 1 is valid

    # Act
    result = _remove_extra_refs(response, refs)

    # Assert
    assert "<sup>1</sup>" in result
    assert "<sup>2</sup>" not in result
    assert "<sup>3</sup>" not in result


@pytest.mark.ai
def test_remove_extra_refs__preserves_valid_refs__in_text(
    refs_list: list[dict[str, Any]],
) -> None:
    """
    Purpose: Verify _remove_extra_refs preserves refs that are in the refs list.
    Why this matters: Ensures valid references remain intact.
    Setup summary: Text with valid refs, verify all preserved.
    """
    # Arrange
    response = "First <sup>1</sup> and second <sup>2</sup>"

    # Act
    result = _remove_extra_refs(response, refs_list)

    # Assert
    assert result == response


@pytest.mark.ai
def test_remove_extra_refs__removes_all_refs__when_refs_list_empty() -> None:
    """
    Purpose: Verify all refs removed when refs list is empty.
    Why this matters: Cleans up all references when none are valid.
    Setup summary: Text with refs, empty refs list, verify all removed.
    """
    # Arrange
    response = "Has <sup>1</sup> and <sup>2</sup>"
    refs: list[dict[str, Any]] = []

    # Act
    result = _remove_extra_refs(response, refs)

    # Assert
    assert "<sup>" not in result
    assert result == "Has  and "


@pytest.mark.ai
def test_remove_extra_refs__handles_multiple_occurrences__of_same_ref() -> None:
    """
    Purpose: Verify removes all occurrences of an orphan ref.
    Why this matters: Ensures complete cleanup of invalid refs.
    Setup summary: Text with repeated orphan ref, verify all instances removed.
    """
    # Arrange
    response = "First <sup>3</sup> middle <sup>3</sup> end <sup>3</sup>"
    refs = [{"sequenceNumber": 1}]  # Ref 3 is orphan

    # Act
    result = _remove_extra_refs(response, refs)

    # Assert
    assert "<sup>3</sup>" not in result
    assert result == "First  middle  end "


# Tests for _prepare_sub_agent_response_refs


@pytest.mark.ai
def test_prepare_sub_agent_response_refs__replaces_ref_format__correctly() -> None:
    """
    Purpose: Verify refs are replaced with sub-agent format.
    Why this matters: Core functionality for sub-agent reference attribution.
    Setup summary: Text with standard refs, verify replaced with named format.
    """
    # Arrange
    response = "Check this <sup>1</sup> reference"
    name = "ResearchAgent"
    sequence_number = 1
    refs = [{"sequenceNumber": 1}]

    # Act
    result = _prepare_sub_agent_response_refs(response, name, sequence_number, refs)

    # Assert
    assert "<sup>1</sup>" not in result
    assert "<sup><name>ResearchAgent 1</name>1</sup>" in result


@pytest.mark.ai
def test_prepare_sub_agent_response_refs__handles_multiple_refs__correctly() -> None:
    """
    Purpose: Verify multiple refs are all properly formatted.
    Why this matters: Ensures batch processing of references works.
    Setup summary: Text with multiple refs, verify all replaced correctly.
    """
    # Arrange
    response = "First <sup>1</sup> and second <sup>2</sup>"
    name = "TestAgent"
    sequence_number = 3
    refs = [{"sequenceNumber": 1}, {"sequenceNumber": 2}]

    # Act
    result = _prepare_sub_agent_response_refs(response, name, sequence_number, refs)

    # Assert
    assert "<sup><name>TestAgent 3</name>1</sup>" in result
    assert "<sup><name>TestAgent 3</name>2</sup>" in result


@pytest.mark.ai
def test_prepare_sub_agent_response_refs__preserves_text__around_refs() -> None:
    """
    Purpose: Verify surrounding text is preserved when refs are replaced.
    Why this matters: Ensures reference replacement doesn't corrupt text.
    Setup summary: Text with refs, verify non-ref content unchanged.
    """
    # Arrange
    response = "Start text <sup>1</sup> middle text <sup>2</sup> end text"
    name = "Agent"
    sequence_number = 1
    refs = [{"sequenceNumber": 1}, {"sequenceNumber": 2}]

    # Act
    result = _prepare_sub_agent_response_refs(response, name, sequence_number, refs)

    # Assert
    assert "Start text" in result
    assert "middle text" in result
    assert "end text" in result


@pytest.mark.ai
def test_prepare_sub_agent_response_refs__returns_unchanged__when_no_refs() -> None:
    """
    Purpose: Verify text unchanged when refs list is empty.
    Why this matters: Handles edge case of no references gracefully.
    Setup summary: Empty refs list, verify text unchanged.
    """
    # Arrange
    response = "Text without any references"
    name = "Agent"
    sequence_number = 1
    refs: list[dict[str, Any]] = []

    # Act
    result = _prepare_sub_agent_response_refs(response, name, sequence_number, refs)

    # Assert
    assert result == response


@pytest.mark.ai
def test_prepare_sub_agent_response_refs__uses_correct_sequence_number__in_format() -> (
    None
):
    """
    Purpose: Verify the sequence number is correctly used in the formatted reference.
    Why this matters: Sequence number identifies the sub-agent call instance.
    Setup summary: Specific sequence number, verify it appears in output format.
    """
    # Arrange
    response = "Ref <sup>1</sup>"
    name = "MyAgent"
    sequence_number = 42
    refs = [{"sequenceNumber": 1}]

    # Act
    result = _prepare_sub_agent_response_refs(response, name, sequence_number, refs)

    # Assert
    assert "<name>MyAgent 42</name>" in result


# Tests for _get_sub_agent_system_reminders


@pytest.mark.ai
def test_get_sub_agent_system_reminders__returns_empty__when_no_configs() -> None:
    """
    Purpose: Verify returns empty list when no reminder configs provided.
    Why this matters: Handles no-config case gracefully.
    Setup summary: Empty configs list, assert empty result.
    """
    # Arrange
    response = "Some response"
    configs: list[Any] = []
    name = "TestAgent"
    display_name = "Test Agent"
    sequence_number = 1
    has_refs = False

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert result == []


@pytest.mark.ai
def test_get_sub_agent_system_reminders__adds_fixed_reminder__always() -> None:
    """
    Purpose: Verify FIXED type reminders are always added.
    Why this matters: FIXED reminders should appear regardless of response content.
    Setup summary: FIXED config, verify reminder added.
    """
    # Arrange
    response = "Any response"
    configs = [FixedSystemReminderConfig(reminder="Always show this reminder")]
    name = "TestAgent"
    display_name = "Test Agent"
    sequence_number = 1
    has_refs = False

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert len(result) == 1
    assert "Always show this reminder" in result[0]


@pytest.mark.ai
def test_get_sub_agent_system_reminders__adds_reference_reminder__when_has_refs() -> (
    None
):
    """
    Purpose: Verify REFERENCE type reminder added when has_refs is True.
    Why this matters: Reference reminders help LLM cite sources correctly.
    Setup summary: REFERENCE config with has_refs=True, verify reminder added.
    """
    # Arrange
    response = "Response with refs"
    configs = [ReferenceSystemReminderConfig()]
    name = "TestAgent"
    display_name = "Test Agent"
    sequence_number = 1
    has_refs = True

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert len(result) == 1
    assert "Test Agent" in result[0]  # display_name should be rendered


@pytest.mark.ai
def test_get_sub_agent_system_reminders__skips_reference_reminder__when_no_refs() -> (
    None
):
    """
    Purpose: Verify REFERENCE reminder skipped when has_refs is False.
    Why this matters: Avoids irrelevant reminders about citations.
    Setup summary: REFERENCE config with has_refs=False, verify not added.
    """
    # Arrange
    response = "Response without refs"
    configs = [ReferenceSystemReminderConfig()]
    name = "TestAgent"
    display_name = "Test Agent"
    sequence_number = 1
    has_refs = False

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert result == []


@pytest.mark.ai
def test_get_sub_agent_system_reminders__adds_no_reference_reminder__when_no_refs() -> (
    None
):
    """
    Purpose: Verify NO_REFERENCE reminder added when has_refs is False.
    Why this matters: Warns LLM not to fabricate citations.
    Setup summary: NO_REFERENCE config with has_refs=False, verify added.
    """
    # Arrange
    response = "Response without refs"
    configs = [NoReferenceSystemReminderConfig()]
    name = "TestAgent"
    display_name = "Test Agent"
    sequence_number = 1
    has_refs = False

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert len(result) == 1
    assert "NOT" in result[0]  # Default reminder contains "Do NOT"


@pytest.mark.ai
def test_get_sub_agent_system_reminders__skips_no_reference_reminder__when_has_refs() -> (
    None
):
    """
    Purpose: Verify NO_REFERENCE reminder skipped when has_refs is True.
    Why this matters: Avoids contradictory instructions when refs exist.
    Setup summary: NO_REFERENCE config with has_refs=True, verify not added.
    """
    # Arrange
    response = "Response with refs"
    configs = [NoReferenceSystemReminderConfig()]
    name = "TestAgent"
    display_name = "Test Agent"
    sequence_number = 1
    has_refs = True

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert result == []


@pytest.mark.ai
def test_get_sub_agent_system_reminders__adds_regexp_reminder__when_pattern_matches() -> (
    None
):
    """
    Purpose: Verify REGEXP reminder added when pattern matches response.
    Why this matters: Enables conditional reminders based on response content.
    Setup summary: REGEXP config matching response, verify reminder added.
    """
    # Arrange
    response = "This response contains IMPORTANT_KEYWORD here"
    configs = [
        RegExpDetectedSystemReminderConfig(
            regexp=re.compile(r"IMPORTANT_KEYWORD"),
            reminder="Found keyword: {{ text_matches }}",
        )
    ]
    name = "TestAgent"
    display_name = "Test Agent"
    sequence_number = 1
    has_refs = False

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert len(result) == 1
    assert "IMPORTANT_KEYWORD" in result[0]


@pytest.mark.ai
def test_get_sub_agent_system_reminders__skips_regexp_reminder__when_no_match() -> None:
    """
    Purpose: Verify REGEXP reminder skipped when pattern doesn't match.
    Why this matters: Avoids irrelevant conditional reminders.
    Setup summary: REGEXP config not matching response, verify not added.
    """
    # Arrange
    response = "This response has no special keywords"
    configs = [
        RegExpDetectedSystemReminderConfig(
            regexp=re.compile(r"NONEXISTENT_PATTERN"),
            reminder="Should not appear",
        )
    ]
    name = "TestAgent"
    display_name = "Test Agent"
    sequence_number = 1
    has_refs = False

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert result == []


@pytest.mark.ai
def test_get_sub_agent_system_reminders__renders_jinja_template__correctly() -> None:
    """
    Purpose: Verify Jinja templates in reminders are correctly rendered.
    Why this matters: Templates allow dynamic reminder content.
    Setup summary: FIXED config with template placeholders, verify rendered.
    """
    # Arrange
    response = "Some response"
    configs = [
        FixedSystemReminderConfig(
            reminder="Tool {{ tool_name }} ({{ display_name }}) says hello"
        )
    ]
    name = "MyTool"
    display_name = "My Special Tool"
    sequence_number = 1
    has_refs = False

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert len(result) == 1
    assert "Tool MyTool (My Special Tool) says hello" in result[0]


@pytest.mark.ai
def test_get_sub_agent_system_reminders__includes_sequence_in_tool_name__for_ref_types() -> (
    None
):
    """
    Purpose: Verify REFERENCE/NO_REFERENCE types include sequence number in tool_name.
    Why this matters: Helps identify which sub-agent call produced the response.
    Setup summary: REFERENCE config, verify tool_name includes sequence number.
    """
    # Arrange
    response = "Response"
    configs = [ReferenceSystemReminderConfig(reminder="Cite {{ tool_name }} correctly")]
    name = "Agent"
    display_name = "Agent"
    sequence_number = 5
    has_refs = True

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert len(result) == 1
    assert "Agent 5" in result[0]


@pytest.mark.ai
def test_get_sub_agent_system_reminders__handles_multiple_configs__correctly() -> None:
    """
    Purpose: Verify multiple configs are processed and applicable ones added.
    Why this matters: Supports complex reminder configurations.
    Setup summary: Multiple config types, verify correct ones added.
    """
    # Arrange
    response = "Response with SPECIAL text"
    configs = [
        FixedSystemReminderConfig(reminder="Fixed reminder"),
        NoReferenceSystemReminderConfig(),  # Should be added (has_refs=False)
        ReferenceSystemReminderConfig(),  # Should NOT be added (has_refs=False)
        RegExpDetectedSystemReminderConfig(
            regexp=re.compile(r"SPECIAL"),
            reminder="Found special",
        ),
    ]
    name = "TestAgent"
    display_name = "Test Agent"
    sequence_number = 1
    has_refs = False

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert len(result) == 3
    assert any("Fixed reminder" in r for r in result)
    assert any("NOT" in r for r in result)  # NO_REFERENCE default
    assert any("Found special" in r for r in result)


@pytest.mark.ai
def test_get_sub_agent_system_reminders__captures_all_regexp_matches__in_text_matches() -> (
    None
):
    """
    Purpose: Verify all regexp matches are captured in text_matches variable.
    Why this matters: Allows templates to reference all matched content.
    Setup summary: Response with multiple pattern matches, verify all captured.
    """
    # Arrange
    response = "Found CODE123 and CODE456 and CODE789"
    configs = [
        RegExpDetectedSystemReminderConfig(
            regexp=re.compile(r"CODE\d+"),
            reminder="Codes found: {{ text_matches | join(', ') }}",
        )
    ]
    name = "TestAgent"
    display_name = "Test Agent"
    sequence_number = 1
    has_refs = False

    # Act
    result = _get_sub_agent_system_reminders(
        response, configs, name, display_name, sequence_number, has_refs
    )

    # Assert
    assert len(result) == 1
    assert "CODE123" in result[0]
    assert "CODE456" in result[0]
    assert "CODE789" in result[0]
