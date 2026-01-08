"""
Tests for FeatureFlags settings class.

This file tests the feature flags functionality that loads configuration
from environment variables and provides utility methods to check feature
enablement.
"""

import os
from unittest.mock import patch

import pytest

from unique_toolkit.agentic.feature_flags.feature_flags import FeatureFlags


# Default Value Tests
@pytest.mark.ai
def test_feature_flags__has_empty_default__for_new_answers_ui_flag_AI() -> None:
    """
    Purpose: Verify feature flag has empty string as default value.
    Why this matters: Default should disable the feature when not configured.
    Setup summary: Create FeatureFlags with no env vars, verify default value.
    """
    # Arrange
    with patch.dict(os.environ, {}, clear=True):
        # Act
        flags = FeatureFlags()

        # Assert
        assert flags.feature_flag_enable_new_answers_ui_un_14411 == ""


@pytest.mark.ai
def test_feature_flags__loads_value_from_env__for_new_answers_ui_flag_AI() -> None:
    """
    Purpose: Verify feature flag loads value from environment variable.
    Why this matters: Feature flags must be configurable via environment.
    Setup summary: Set env var, create FeatureFlags, verify value is loaded.
    """
    # Arrange
    env_value = "company1,company2"
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": env_value},
        clear=True,
    ):
        # Act
        flags = FeatureFlags()

        # Assert
        assert flags.feature_flag_enable_new_answers_ui_un_14411 == env_value


@pytest.mark.ai
def test_feature_flags__loads_lowercase_env_var__case_insensitive_AI() -> None:
    """
    Purpose: Verify feature flag loads from lowercase env var name.
    Why this matters: Environment variable names should be case-insensitive.
    Setup summary: Set lowercase env var, create FeatureFlags, verify value is loaded.
    """
    # Arrange
    env_value = "true"
    with patch.dict(
        os.environ,
        {"feature_flag_enable_new_answers_ui_un_14411": env_value},
        clear=True,
    ):
        # Act
        flags = FeatureFlags()

        # Assert
        assert flags.feature_flag_enable_new_answers_ui_un_14411 == env_value


# is_new_answers_ui_enabled Tests - Empty/Default Value
@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_false__when_flag_is_empty_AI() -> None:
    """
    Purpose: Verify method returns False when flag value is empty string.
    Why this matters: Empty value should mean feature is disabled.
    Setup summary: Create FeatureFlags with empty flag, call method, verify False.
    """
    # Arrange
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled()

        # Assert
        assert result is False


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_false__when_flag_is_empty_with_company_id_AI() -> (
    None
):
    """
    Purpose: Verify method returns False when flag is empty even with company_id.
    Why this matters: Empty value means feature disabled for all companies.
    Setup summary: Create FeatureFlags with empty flag, call with company_id, verify False.
    """
    # Arrange
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id="company1")

        # Assert
        assert result is False


# is_new_answers_ui_enabled Tests - "true" Value
@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_true__when_flag_is_true_lowercase_AI() -> (
    None
):
    """
    Purpose: Verify method returns True when flag value is "true".
    Why this matters: "true" should enable feature for all companies.
    Setup summary: Set flag to "true", call method without company_id, verify True.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "true"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled()

        # Assert
        assert result is True


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_true__when_flag_is_true_uppercase_AI() -> (
    None
):
    """
    Purpose: Verify method returns True when flag value is "TRUE" (uppercase).
    Why this matters: "true" check should be case-insensitive.
    Setup summary: Set flag to "TRUE", call method, verify True.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "TRUE"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled()

        # Assert
        assert result is True


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_true__when_flag_is_true_mixed_case_AI() -> (
    None
):
    """
    Purpose: Verify method returns True when flag value is "True" (mixed case).
    Why this matters: "true" check should be case-insensitive.
    Setup summary: Set flag to "True", call method, verify True.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "True"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled()

        # Assert
        assert result is True


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_true__when_flag_is_true_with_company_id_AI() -> (
    None
):
    """
    Purpose: Verify method returns True when flag is "true" even with company_id.
    Why this matters: "true" enables for all, company_id should not affect result.
    Setup summary: Set flag to "true", call with company_id, verify True.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "true"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id="company1")

        # Assert
        assert result is True


# is_new_answers_ui_enabled Tests - Comma-Separated Company IDs
@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_true__when_company_id_in_list_AI() -> None:
    """
    Purpose: Verify method returns True when company_id is in the list.
    Why this matters: Feature should be enabled for listed companies.
    Setup summary: Set flag to comma-separated list, call with matching company_id.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1,company2,company3"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id="company2")

        # Assert
        assert result is True


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_true__when_company_id_is_first_in_list_AI() -> (
    None
):
    """
    Purpose: Verify method returns True when company_id is first in list.
    Why this matters: Position in list should not affect matching.
    Setup summary: Set flag to comma-separated list, call with first company_id.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1,company2"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id="company1")

        # Assert
        assert result is True


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_true__when_company_id_is_last_in_list_AI() -> (
    None
):
    """
    Purpose: Verify method returns True when company_id is last in list.
    Why this matters: Position in list should not affect matching.
    Setup summary: Set flag to comma-separated list, call with last company_id.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1,company2"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id="company2")

        # Assert
        assert result is True


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_false__when_company_id_not_in_list_AI() -> (
    None
):
    """
    Purpose: Verify method returns False when company_id is not in the list.
    Why this matters: Feature should be disabled for unlisted companies.
    Setup summary: Set flag to comma-separated list, call with non-matching company_id.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1,company2"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id="company3")

        # Assert
        assert result is False


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_false__when_company_id_is_none_with_list_AI() -> (
    None
):
    """
    Purpose: Verify method returns False when company_id is None with comma-separated list.
    Why this matters: None company_id cannot match any specific company in list.
    Setup summary: Set flag to comma-separated list, call with None company_id.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1,company2"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id=None)

        # Assert
        assert result is False


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_false__when_no_company_id_with_list_AI() -> (
    None
):
    """
    Purpose: Verify method returns False when company_id not provided with comma-separated list.
    Why this matters: Without company_id, cannot check list membership.
    Setup summary: Set flag to comma-separated list, call without company_id argument.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1,company2"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled()

        # Assert
        assert result is False


# is_new_answers_ui_enabled Tests - Single Company ID
@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_true__with_single_company_id_AI() -> None:
    """
    Purpose: Verify method returns True when flag is single company_id that matches.
    Why this matters: Single company should work without comma separation.
    Setup summary: Set flag to single company_id, call with matching company_id.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id="company1")

        # Assert
        assert result is True


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_false__with_single_company_id_no_match_AI() -> (
    None
):
    """
    Purpose: Verify method returns False when flag is single company_id that doesn't match.
    Why this matters: Non-matching company should not be enabled.
    Setup summary: Set flag to single company_id, call with different company_id.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id="company2")

        # Assert
        assert result is False


# is_new_answers_ui_enabled Tests - Edge Cases
@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_false__when_partial_company_id_match_AI() -> (
    None
):
    """
    Purpose: Verify method returns False for partial company_id matches.
    Why this matters: "company" should not match "company1" - exact match required.
    Setup summary: Set flag to "company1", call with "company", verify False.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id="company")

        # Assert
        assert result is False


@pytest.mark.ai
def test_is_new_answers_ui_enabled__returns_false__when_company_id_is_empty_string_AI() -> (
    None
):
    """
    Purpose: Verify method returns False when company_id is empty string with list.
    Why this matters: Empty string should not match any company in list.
    Setup summary: Set flag to comma-separated list, call with empty string.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1,company2"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result = flags.is_new_answers_ui_enabled(company_id="")

        # Assert
        assert result is False


@pytest.mark.ai
def test_is_new_answers_ui_enabled__handles_whitespace_in_company_ids_AI() -> None:
    """
    Purpose: Verify whitespace in company IDs is preserved (not trimmed).
    Why this matters: Exact matching means whitespace affects results.
    Setup summary: Set flag with spaces, verify behavior.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {"FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "company1, company2"},
        clear=True,
    ):
        flags = FeatureFlags()

        # Act
        result_with_space = flags.is_new_answers_ui_enabled(company_id=" company2")
        result_without_space = flags.is_new_answers_ui_enabled(company_id="company2")

        # Assert
        assert result_with_space is True
        assert result_without_space is False


# Module-level Singleton Tests
@pytest.mark.ai
def test_feature_flags__module_singleton_exists__AI() -> None:
    """
    Purpose: Verify feature_flags singleton is importable.
    Why this matters: Module should provide pre-initialized singleton for convenience.
    Setup summary: Import feature_flags, verify it's a FeatureFlags instance.
    """
    # Arrange & Act
    from unique_toolkit.agentic.feature_flags.feature_flags import feature_flags

    # Assert
    assert isinstance(feature_flags, FeatureFlags)


# Extra Fields Handling Tests
@pytest.mark.ai
def test_feature_flags__ignores_extra_env_vars__AI() -> None:
    """
    Purpose: Verify FeatureFlags ignores unknown environment variables.
    Why this matters: extra="ignore" setting should prevent errors on unknown fields.
    Setup summary: Set extra env var, create FeatureFlags, verify no error.
    """
    # Arrange
    with patch.dict(
        os.environ,
        {
            "FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": "true",
            "SOME_OTHER_ENV_VAR": "value",
        },
        clear=True,
    ):
        # Act
        flags = FeatureFlags()

        # Assert
        assert flags.feature_flag_enable_new_answers_ui_un_14411 == "true"
        assert not hasattr(flags, "some_other_env_var")

