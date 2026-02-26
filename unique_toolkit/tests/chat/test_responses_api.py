"""Tests for responses_api.py JSON parsing functionality."""

import pytest

from unique_toolkit.chat.responses_api import (
    _attempt_extract_reasoning_from_options,
    _attempt_extract_verbosity_from_options,
)

# ============================================================================
# Tests for _attempt_extract_reasoning_from_options
# ============================================================================


@pytest.mark.ai
def test_extract_reasoning__parses_json_string__correctly() -> None:
    """
    Purpose: Verify reasoning parameter is parsed from JSON string (UI compatibility).
    Why this matters: UI sends reasoning as JSON string due to limitations.
    Setup summary: Pass reasoning as JSON string, verify it's parsed to dict.
    """
    # Arrange
    options = {"reasoning": '{"effort": "high"}'}

    # Act
    result = _attempt_extract_reasoning_from_options(options)

    # Assert
    assert result is not None
    assert result["effort"] == "high"


@pytest.mark.ai
def test_extract_reasoning__handles_dict__correctly() -> None:
    """
    Purpose: Verify reasoning parameter works with dict input (non-UI clients).
    Why this matters: Direct API calls pass reasoning as dict.
    Setup summary: Pass reasoning as dict, verify it's returned correctly.
    """
    # Arrange
    options = {"reasoning": {"effort": "low"}}

    # Act
    result = _attempt_extract_reasoning_from_options(options)

    # Assert
    assert result is not None
    assert result["effort"] == "low"


@pytest.mark.ai
def test_extract_reasoning__handles_invalid_json__gracefully() -> None:
    """
    Purpose: Verify invalid JSON string doesn't crash, logs warning.
    Why this matters: Malformed input must not break the API pipeline.
    Setup summary: Pass invalid JSON, verify None returned (failsafe).
    """
    # Arrange
    options = {"reasoning": '{"invalid": json}'}

    # Act
    result = _attempt_extract_reasoning_from_options(options)

    # Assert
    # Function has @failsafe decorator, should return None for invalid input
    assert result is None


@pytest.mark.ai
def test_extract_reasoning__returns_none__when_missing() -> None:
    """
    Purpose: Verify function returns None when reasoning not in options.
    Why this matters: Optional parameters must not cause errors.
    Setup summary: Pass options without reasoning, verify None returned.
    """
    # Arrange
    options = {"temperature": 0.7}

    # Act
    result = _attempt_extract_reasoning_from_options(options)

    # Assert
    assert result is None


# ============================================================================
# Tests for _attempt_extract_verbosity_from_options
# ============================================================================


@pytest.mark.ai
def test_extract_verbosity__parses_json_string__correctly() -> None:
    """
    Purpose: Verify text config is parsed from JSON string (UI compatibility).
    Why this matters: UI sends text config as JSON string due to limitations.
    Setup summary: Pass text as JSON string, verify it's parsed to dict.
    """
    # Arrange
    options = {"text": '{"verbosity": "high"}'}

    # Act
    result = _attempt_extract_verbosity_from_options(options)

    # Assert
    assert result is not None
    assert result["verbosity"] == "high"


@pytest.mark.ai
def test_extract_verbosity__handles_dict__correctly() -> None:
    """
    Purpose: Verify text config works with dict input (non-UI clients).
    Why this matters: Direct API calls pass text config as dict.
    Setup summary: Pass text as dict, verify it's returned correctly.
    """
    # Arrange
    options = {"text": {"verbosity": "medium"}}

    # Act
    result = _attempt_extract_verbosity_from_options(options)

    # Assert
    assert result is not None
    assert result["verbosity"] == "medium"


@pytest.mark.ai
def test_extract_verbosity__handles_invalid_json__gracefully() -> None:
    """
    Purpose: Verify invalid JSON string doesn't crash, logs warning.
    Why this matters: Malformed input must not break the API pipeline.
    Setup summary: Pass invalid JSON, verify None returned (failsafe).
    """
    # Arrange
    options = {"text": '{"invalid": json}'}

    # Act
    result = _attempt_extract_verbosity_from_options(options)

    # Assert
    # Function has @failsafe decorator, should return None for invalid input
    assert result is None


@pytest.mark.ai
def test_extract_verbosity__returns_none__when_missing() -> None:
    """
    Purpose: Verify function returns None when text not in options.
    Why this matters: Optional parameters must not cause errors.
    Setup summary: Pass options without text, verify None returned.
    """
    # Arrange
    options = {"temperature": 0.7}

    # Act
    result = _attempt_extract_verbosity_from_options(options)

    # Assert
    assert result is None


@pytest.mark.ai
def test_extract_verbosity__uses_correct_variable_name() -> None:
    """
    Purpose: Verify variable name bug fix - uses text_config not reasoning.
    Why this matters: This was a bug in the original code that was fixed.
    Setup summary: Pass text config, verify it's processed with correct variable.
    """
    # Arrange
    options = {"text": {"verbosity": "low"}}

    # Act
    result = _attempt_extract_verbosity_from_options(options)

    # Assert
    # This test ensures the variable name bug is fixed
    assert result is not None
    assert result["verbosity"] == "low"
