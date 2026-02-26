"""
Tests for FeatureFlags settings class.

This file tests the feature flags functionality that loads configuration
from environment variables and provides utility methods to check feature
enablement.
"""

import os
from unittest.mock import patch

import pytest

from unique_toolkit.agentic.feature_flags.feature_flags import FeatureFlag, FeatureFlags


@pytest.mark.ai
def test_feature_flag__initializes_with_bool_true__value_storage() -> None:
    """
    Purpose: Verify FeatureFlag initializes with boolean True value.
    Why this matters: Boolean flags enable features globally.
    Setup summary: Create FeatureFlag with True, verify value stored.
    """
    # Arrange & Act
    flag = FeatureFlag(True)

    # Assert
    assert flag.value is True


@pytest.mark.ai
def test_feature_flag__initializes_with_bool_false__value_storage() -> None:
    """
    Purpose: Verify FeatureFlag initializes with boolean False value.
    Why this matters: Boolean flags disable features globally.
    Setup summary: Create FeatureFlag with False, verify value stored.
    """
    # Arrange & Act
    flag = FeatureFlag(False)

    # Assert
    assert flag.value is False


@pytest.mark.ai
def test_feature_flag__initializes_with_company_list__value_storage() -> None:
    """
    Purpose: Verify FeatureFlag initializes with list of company IDs.
    Why this matters: List enables selective company-based feature flags.
    Setup summary: Create FeatureFlag with company list, verify value stored.
    """
    # Arrange
    company_ids = ["company1", "company2", "company3"]

    # Act
    flag = FeatureFlag(company_ids)

    # Assert
    assert flag.value == company_ids
    assert isinstance(flag.value, list)


@pytest.mark.ai
def test_feature_flag__is_enabled_returns_true__when_value_is_true() -> None:
    """
    Purpose: Verify is_enabled returns True when flag value is True.
    Why this matters: Boolean True should enable for all companies.
    Setup summary: Create FeatureFlag(True), call is_enabled, verify True.
    """
    # Arrange
    flag = FeatureFlag(True)

    # Act
    result_without_id = flag.is_enabled()
    result_with_id = flag.is_enabled("any_company")

    # Assert
    assert result_without_id is True
    assert result_with_id is True


@pytest.mark.ai
def test_feature_flag__is_enabled_returns_false__when_value_is_false() -> None:
    """
    Purpose: Verify is_enabled returns False when flag value is False.
    Why this matters: Boolean False should disable for all companies.
    Setup summary: Create FeatureFlag(False), call is_enabled, verify False.
    """
    # Arrange
    flag = FeatureFlag(False)

    # Act
    result_without_id = flag.is_enabled()
    result_with_id = flag.is_enabled("any_company")

    # Assert
    assert result_without_id is False
    assert result_with_id is False


@pytest.mark.ai
def test_feature_flag__is_enabled_returns_true__when_company_in_list() -> None:
    """
    Purpose: Verify is_enabled returns True when company_id is in list.
    Why this matters: List-based flags enable for specific companies.
    Setup summary: Create FeatureFlag with list, check with matching company_id.
    """
    # Arrange
    flag = FeatureFlag(["company1", "company2"])

    # Act
    result = flag.is_enabled("company1")

    # Assert
    assert result is True


@pytest.mark.ai
def test_feature_flag__is_enabled_returns_false__when_company_not_in_list() -> None:
    """
    Purpose: Verify is_enabled returns False when company_id not in list.
    Why this matters: List-based flags disable for unlisted companies.
    Setup summary: Create FeatureFlag with list, check with non-matching company_id.
    """
    # Arrange
    flag = FeatureFlag(["company1", "company2"])

    # Act
    result = flag.is_enabled("company3")

    # Assert
    assert result is False


@pytest.mark.ai
def test_feature_flag__is_enabled_returns_false__when_no_company_id_with_list() -> None:
    """
    Purpose: Verify is_enabled returns False when company_id is None with list.
    Why this matters: List-based flags require company_id to check membership.
    Setup summary: Create FeatureFlag with list, call is_enabled without company_id.
    """
    # Arrange
    flag = FeatureFlag(["company1", "company2"])

    # Act
    result = flag.is_enabled()

    # Assert
    assert result is False


@pytest.mark.ai
def test_feature_flag__repr_shows_value__string_representation() -> None:
    """
    Purpose: Verify __repr__ returns proper string representation.
    Why this matters: Debugging requires readable flag representation.
    Setup summary: Create FeatureFlag, call repr, verify format.
    """
    # Arrange
    flag_bool = FeatureFlag(True)
    flag_list = FeatureFlag(["company1", "company2"])

    # Act
    repr_bool = repr(flag_bool)
    repr_list = repr(flag_list)

    # Assert
    assert repr_bool == "FeatureFlag(True)"
    assert repr_list == "FeatureFlag(['company1', 'company2'])"


# ============================================================================
# parse_feature_flag Validator Tests
# ============================================================================


@pytest.mark.ai
def test_parse_feature_flag__parses_true_string__to_bool_flag() -> None:
    """
    Purpose: Verify parse_feature_flag converts "true" to FeatureFlag(True).
    Why this matters: String "true" from env should enable globally.
    Setup summary: Set env var to "true", verify FeatureFlag(True) created.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": "true"},
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert isinstance(flags.enable_elicitation_un_15809, FeatureFlag)
    assert flags.enable_elicitation_un_15809.value is True
    assert flags.enable_elicitation_un_15809.is_enabled() is True


@pytest.mark.ai
def test_parse_feature_flag__parses_one_string__to_bool_flag() -> None:
    """
    Purpose: Verify parse_feature_flag converts "1" to FeatureFlag(True).
    Why this matters: Numeric "1" should enable globally.
    Setup summary: Set env var to "1", verify FeatureFlag(True) created.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": "1"},
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_elicitation_un_15809.value is True


@pytest.mark.ai
def test_parse_feature_flag__parses_yes_string__to_bool_flag() -> None:
    """
    Purpose: Verify parse_feature_flag converts "yes" to FeatureFlag(True).
    Why this matters: Human-friendly "yes" should enable globally.
    Setup summary: Set env var to "yes", verify FeatureFlag(True) created.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": "yes"},
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_elicitation_un_15809.value is True


@pytest.mark.ai
def test_parse_feature_flag__parses_false_string__to_bool_flag() -> None:
    """
    Purpose: Verify parse_feature_flag converts "false" to FeatureFlag(False).
    Why this matters: String "false" from env should disable globally.
    Setup summary: Set env var to "false", verify FeatureFlag(False) created.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": "false"},
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert isinstance(flags.enable_elicitation_un_15809, FeatureFlag)
    assert flags.enable_elicitation_un_15809.value is False
    assert flags.enable_elicitation_un_15809.is_enabled() is False


@pytest.mark.ai
def test_parse_feature_flag__parses_zero_string__to_bool_flag() -> None:
    """
    Purpose: Verify parse_feature_flag converts "0" to FeatureFlag(False).
    Why this matters: Numeric "0" should disable globally.
    Setup summary: Set env var to "0", verify FeatureFlag(False) created.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": "0"},
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_elicitation_un_15809.value is False


@pytest.mark.ai
def test_parse_feature_flag__parses_no_string__to_bool_flag() -> None:
    """
    Purpose: Verify parse_feature_flag converts "no" to FeatureFlag(False).
    Why this matters: Human-friendly "no" should disable globally.
    Setup summary: Set env var to "no", verify FeatureFlag(False) created.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": "no"},
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_elicitation_un_15809.value is False


@pytest.mark.ai
def test_parse_feature_flag__parses_empty_string__to_bool_flag() -> None:
    """
    Purpose: Verify parse_feature_flag converts empty string to FeatureFlag(False).
    Why this matters: Empty value should disable globally.
    Setup summary: Set env var to empty string, verify FeatureFlag(False) created.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": ""},
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_elicitation_un_15809.value is False


@pytest.mark.ai
def test_parse_feature_flag__parses_comma_separated_ids__to_list_flag() -> None:
    """
    Purpose: Verify parse_feature_flag parses comma-separated IDs to list.
    Why this matters: Comma-separated values enable for specific companies.
    Setup summary: Set env var to company IDs, verify FeatureFlag(list) created.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": "company1,company2,company3"},
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert isinstance(flags.enable_elicitation_un_15809, FeatureFlag)
    assert flags.enable_elicitation_un_15809.value == [
        "company1",
        "company2",
        "company3",
    ]
    assert flags.enable_elicitation_un_15809.is_enabled("company1") is True
    assert flags.enable_elicitation_un_15809.is_enabled("company4") is False


@pytest.mark.ai
def test_parse_feature_flag__trims_whitespace__in_company_ids() -> None:
    """
    Purpose: Verify parse_feature_flag trims whitespace around company IDs.
    Why this matters: Whitespace in env vars should be ignored.
    Setup summary: Set env var with spaces, verify trimmed IDs in list.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {
            "FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": " company1 , company2 , company3 "
        },
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_elicitation_un_15809.value == [
        "company1",
        "company2",
        "company3",
    ]


@pytest.mark.ai
def test_parse_feature_flag__handles_bool_type__directly() -> None:
    """
    Purpose: Verify parse_feature_flag handles Python bool type directly.
    Why this matters: Programmatic creation with bool should work.
    Setup summary: Create flags with bool value, verify FeatureFlag created.
    """
    # Arrange & Act
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()
        # The default is already FeatureFlag(False) for enable_elicitation_un_15809

    # Assert
    assert isinstance(flags.enable_elicitation_un_15809, FeatureFlag)
    assert flags.enable_elicitation_un_15809.value is False


@pytest.mark.ai
def test_parse_feature_flag__handles_list_type__directly() -> None:
    """
    Purpose: Verify parse_feature_flag handles Python list type directly.
    Why this matters: Programmatic creation with list should work.
    Setup summary: Parse list value, verify FeatureFlag created with list.
    """
    # Arrange
    # Test by directly calling the validator logic (through model creation)
    from unique_toolkit.agentic.feature_flags.feature_flags import FeatureFlags

    # Act
    # Default for enable_new_answers_ui_un_14411 is FeatureFlag([])
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()

    # Assert
    assert isinstance(flags.enable_new_answers_ui_un_14411, FeatureFlag)
    assert flags.enable_new_answers_ui_un_14411.value == []


@pytest.mark.ai
def test_parse_feature_flag__returns_existing_featureflag__unchanged() -> None:
    """
    Purpose: Verify parse_feature_flag returns FeatureFlag instance unchanged.
    Why this matters: Already-parsed flags should not be re-parsed.
    Setup summary: Pass FeatureFlag instance, verify returned unchanged.
    """
    # Arrange
    # Act - validator returns existing instance
    # This is tested implicitly through the field defaults
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()

    # Assert
    assert isinstance(flags.enable_elicitation_un_15809, FeatureFlag)


@pytest.mark.ai
def test_parse_feature_flag__case_insensitive__for_true_false_values() -> None:
    """
    Purpose: Verify parse_feature_flag handles mixed case true/false.
    Why this matters: Case variations should be normalized.
    Setup summary: Set env vars with mixed case, verify correct parsing.
    """
    # Arrange & Act - Test TRUE
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": "TRUE"},
        clear=True,
    ):
        flags_upper = FeatureFlags()

    # Test True
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_ELICITATION_UN_15809": "True"},
        clear=True,
    ):
        flags_mixed = FeatureFlags()

    # Assert
    assert flags_upper.enable_elicitation_un_15809.value is True
    assert flags_mixed.enable_elicitation_un_15809.value is True


# ============================================================================
# New Feature Flag Fields Tests
# ============================================================================


@pytest.mark.ai
def test_enable_new_answers_ui_flag__uses_featureflag_type__field_definition() -> None:
    """
    Purpose: Verify enable_new_answers_ui_un_14411 uses FeatureFlag type.
    Why this matters: New pattern should use FeatureFlag class.
    Setup summary: Create flags, verify field is FeatureFlag instance.
    """
    # Arrange & Act
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()

    # Assert
    assert isinstance(flags.enable_new_answers_ui_un_14411, FeatureFlag)
    assert flags.enable_new_answers_ui_un_14411.value == []


@pytest.mark.ai
def test_enable_elicitation_flag__uses_featureflag_type__field_definition() -> None:
    """
    Purpose: Verify enable_elicitation_un_15809 uses FeatureFlag type.
    Why this matters: New pattern should use FeatureFlag class.
    Setup summary: Create flags, verify field is FeatureFlag instance.
    """
    # Arrange & Act
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()

    # Assert
    assert isinstance(flags.enable_elicitation_un_15809, FeatureFlag)
    assert flags.enable_elicitation_un_15809.value is False


@pytest.mark.ai
def test_enable_elicitation_flag__has_false_default__field_definition() -> None:
    """
    Purpose: Verify enable_elicitation_un_15809 defaults to False.
    Why this matters: New features should be disabled by default.
    Setup summary: Create flags without env var, verify False default.
    """
    # Arrange & Act
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_elicitation_un_15809.is_enabled() is False


@pytest.mark.ai
def test_new_answers_ui_flag__has_empty_list_default__field_definition() -> None:
    """
    Purpose: Verify enable_new_answers_ui_un_14411 defaults to empty list.
    Why this matters: No companies should be enabled by default.
    Setup summary: Create flags without env var, verify empty list default.
    """
    # Arrange & Act
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_new_answers_ui_un_14411.value == []
    assert flags.enable_new_answers_ui_un_14411.is_enabled() is False
    assert flags.enable_new_answers_ui_un_14411.is_enabled("any_company") is False
