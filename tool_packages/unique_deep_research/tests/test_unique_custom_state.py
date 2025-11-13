"""
Unit tests for unique_custom/state.py module.
"""

import pytest

from unique_deep_research.unique_custom.state import override_reducer


@pytest.mark.ai
def test_override_reducer__returns_new_value__when_override_type() -> None:
    """
    Purpose: Verify override_reducer returns new value when override type is specified.
    Why this matters: Allows overriding state values in LangGraph workflow.
    Setup summary: Call reducer with override type and verify new value is returned.
    """
    # Arrange
    current_value = ["item1", "item2"]
    new_value = {"type": "override", "value": ["item3"]}

    # Act
    result = override_reducer(current_value, new_value)

    # Assert
    assert result == ["item3"]


@pytest.mark.ai
def test_override_reducer__returns_original_value__when_no_override_type() -> None:
    """
    Purpose: Verify override_reducer returns original value when no override type.
    Why this matters: Ensures normal state updates work as expected.
    Setup summary: Call reducer without override type and verify original value is returned.
    """
    # Arrange
    current_value = ["item1", "item2"]
    new_value = ["item3"]

    # Act
    result = override_reducer(current_value, new_value)

    # Assert
    assert result == ["item1", "item2", "item3"]


@pytest.mark.ai
def test_override_reducer__handles_dict_override__correctly() -> None:
    """
    Purpose: Verify override_reducer handles dict override correctly.
    Why this matters: Supports complex state overrides in LangGraph.
    Setup summary: Call reducer with dict override and verify correct handling.
    """
    # Arrange
    current_value = {"key1": "value1"}
    new_value = {"type": "override", "value": {"key2": "value2"}}

    # Act
    result = override_reducer(current_value, new_value)

    # Assert
    assert result == {"key2": "value2"}
