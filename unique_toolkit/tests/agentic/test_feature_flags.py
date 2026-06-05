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


# ============================================================================
# enable_web_search_argument_screening_un_18741 Tests
# ============================================================================


@pytest.mark.ai
def test_enable_web_search_argument_screening_flag__uses_featureflag_type__field_definition() -> (
    None
):
    """
    Purpose: Verify enable_web_search_argument_screening_un_18741 uses FeatureFlag type.
    Why this matters: All feature flags must use the FeatureFlag class.
    Setup summary: Create flags without env var, verify field is FeatureFlag instance.
    """
    # Arrange & Act
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()

    # Assert
    assert isinstance(flags.enable_web_search_argument_screening_un_18741, FeatureFlag)


@pytest.mark.ai
def test_enable_web_search_argument_screening_flag__has_false_default__field_definition() -> (
    None
):
    """
    Purpose: Verify enable_web_search_argument_screening_un_18741 defaults to False.
    Why this matters: New features should be disabled by default.
    Setup summary: Create flags without env var, verify False default.
    """
    # Arrange & Act
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_web_search_argument_screening_un_18741.value is False
    assert flags.enable_web_search_argument_screening_un_18741.is_enabled() is False


@pytest.mark.ai
def test_enable_web_search_argument_screening_flag__enabled_globally__env_var_true() -> (
    None
):
    """
    Purpose: Verify flag enables globally when env var is set to "true".
    Why this matters: Global enablement must work via environment variable.
    Setup summary: Set env var to "true", verify is_enabled returns True for any company.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_WEB_SEARCH_ARGUMENT_SCREENING_UN_18741": "true"},
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_web_search_argument_screening_un_18741.value is True
    assert (
        flags.enable_web_search_argument_screening_un_18741.is_enabled("company1")
        is True
    )
    assert flags.enable_web_search_argument_screening_un_18741.is_enabled() is True


@pytest.mark.ai
def test_enable_web_search_argument_screening_flag__disabled_globally__env_var_false() -> (
    None
):
    """
    Purpose: Verify flag stays disabled when env var is explicitly "false".
    Why this matters: Explicit disablement via env var must be respected.
    Setup summary: Set env var to "false", verify is_enabled returns False.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_WEB_SEARCH_ARGUMENT_SCREENING_UN_18741": "false"},
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert flags.enable_web_search_argument_screening_un_18741.value is False
    assert (
        flags.enable_web_search_argument_screening_un_18741.is_enabled("company1")
        is False
    )
    assert flags.enable_web_search_argument_screening_un_18741.is_enabled() is False


@pytest.mark.ai
def test_enable_web_search_argument_screening_flag__enabled_for_specific_companies__env_var_list() -> (
    None
):
    """
    Purpose: Verify flag enables only for listed companies when env var contains company IDs.
    Why this matters: Selective rollout per company is a core feature flag capability.
    Setup summary: Set env var to comma-separated company IDs, verify only those are enabled.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {
            "FEATURE_FLAG_ENABLE_WEB_SEARCH_ARGUMENT_SCREENING_UN_18741": "company1,company2"
        },
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert (
        flags.enable_web_search_argument_screening_un_18741.is_enabled("company1")
        is True
    )
    assert (
        flags.enable_web_search_argument_screening_un_18741.is_enabled("company2")
        is True
    )
    assert (
        flags.enable_web_search_argument_screening_un_18741.is_enabled("company3")
        is False
    )
    assert flags.enable_web_search_argument_screening_un_18741.is_enabled() is False


@pytest.mark.ai
def test_enable_web_search_argument_screening_flag__not_enabled_for_unlisted_company__env_var_list() -> (
    None
):
    """
    Purpose: Verify flag returns False for companies not in the allowed list.
    Why this matters: Companies outside the list must not gain access to screened search.
    Setup summary: Set env var to one company, verify a different company is not enabled.
    """
    # Arrange & Act
    with patch.dict(
        os.environ,
        {
            "FEATURE_FLAG_ENABLE_WEB_SEARCH_ARGUMENT_SCREENING_UN_18741": "allowed_company"
        },
        clear=True,
    ):
        flags = FeatureFlags()

    # Assert
    assert (
        flags.enable_web_search_argument_screening_un_18741.is_enabled("other_company")
        is False
    )
