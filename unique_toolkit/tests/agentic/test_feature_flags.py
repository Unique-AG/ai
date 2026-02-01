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


def test_feature_flags__has_empty_default_value() -> None:
    with patch.dict(os.environ, {}, clear=True):
        flags = FeatureFlags()
        assert flags.feature_flag_enable_new_answers_ui_un_14411 == ""
        assert (
            flags.feature_flag_enable_full_history_with_content_and_tools_un_15966 == ""
        )


@pytest.mark.parametrize(
    "env_var, company_id, feature_flag_value",
    [
        ("company1,company2", "company1", True),
        ("company1,company2", "company2", True),
        ("true", "company2", True),
        ("True", "company1", True),
        ("company1,company2", "company3", False),
        ("", "company1", False),
        ("true", "", True),
    ],
)
def test_feature_flags(env_var: str, company_id: str, feature_flag_value: bool) -> None:
    with patch.dict(
        os.environ,
        {
            "FEATURE_FLAG_ENABLE_NEW_ANSWERS_UI_UN_14411": env_var,
            "FEATURE_FLAG_ENABLE_FULL_HISTORY_WITH_CONTENT_AND_TOOLS_UN_15966": env_var,
        },
        clear=True,
    ):
        flags = FeatureFlags()
        assert flags.is_new_answers_ui_enabled(company_id) == feature_flag_value
        assert (
            flags.is_full_history_with_content_and_tools_enabled(company_id)
            == feature_flag_value
        )
