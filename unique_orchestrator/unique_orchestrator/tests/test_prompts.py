from string import Template

import pytest

from agentic_search.prompts import (
    SYSTEM_MESSAGE_TOOL_SELECTION,
    SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX,
    USER_MESSAGE_TOOL_SELECTION,
)


def test_system_message_tool_selection_structure():
    # Check essential components are present
    assert "Knowledge cutoff: $info_cutoff_at" in SYSTEM_MESSAGE_TOOL_SELECTION
    assert "Current date: $current_date" in SYSTEM_MESSAGE_TOOL_SELECTION
    assert "$available_tools" in SYSTEM_MESSAGE_TOOL_SELECTION
    assert (
        "$tool_format_information_for_system_prompt"
        in SYSTEM_MESSAGE_TOOL_SELECTION
    )


def test_system_message_tool_selection_template_substitution():
    # Test template substitution
    template = Template(SYSTEM_MESSAGE_TOOL_SELECTION)
    substituted = template.safe_substitute(
        {
            "info_cutoff_at": "2024-01-01",
            "current_date": "2024-03-14",
            "available_tools": "Tool1, Tool2",
            "tool_format_information_for_system_prompt": "Format instructions here",
        }
    )

    assert "2024-01-01" in substituted
    assert "2024-03-14" in substituted
    assert "Tool1, Tool2" in substituted
    assert "Format instructions here" in substituted


def test_user_message_tool_selection_structure():
    # Check essential components
    assert "$query" in USER_MESSAGE_TOOL_SELECTION


def test_user_message_tool_selection_template_substitution():
    # Test template substitution
    template = Template(USER_MESSAGE_TOOL_SELECTION)
    substituted = template.safe_substitute(
        {"query": "What is the weather today?"}
    )

    assert "What is the weather today?" in substituted


def test_citation_appendix_structure():
    # Check essential components and formatting rules
    assert (
        "[source<source_number>]"
        in SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX
    )
    assert "[source1]" in SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX
    assert "source_number" in SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX


@pytest.mark.parametrize(
    "invalid_source_format",
    [
        "[Source1]",  # Capital S
        "[sources1]",  # Plural
        "[source01]",  # Leading zero
        "[sourceOne]",  # Non-digit
        "[source 1]",  # Space
    ],
)
def test_citation_appendix_source_format_examples(invalid_source_format):
    # Verify example formats are correct and invalid formats are not present
    assert (
        invalid_source_format
        not in SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX
    )
    assert "[source0]" in SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX
    assert "[source1]" in SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX
    assert "[source2]" in SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX


def test_all_messages_are_strings():
    assert isinstance(SYSTEM_MESSAGE_TOOL_SELECTION, str)
    assert isinstance(USER_MESSAGE_TOOL_SELECTION, str)
    assert isinstance(SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX, str)


def test_template_variables_consistency():
    # Check all template variables are properly formatted
    system_vars = {
        var[1]
        for var in Template.pattern.findall(SYSTEM_MESSAGE_TOOL_SELECTION)
    }
    user_vars = {
        var[1] for var in Template.pattern.findall(USER_MESSAGE_TOOL_SELECTION)
    }

    # Expected variables
    expected_system_vars = {
        "info_cutoff_at",
        "current_date",
        "available_tools",
        "tool_format_information_for_system_prompt",
    }
    expected_user_vars = {"query"}

    assert system_vars == expected_system_vars
    assert user_vars == expected_user_vars
