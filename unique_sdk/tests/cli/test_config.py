"""Tests for unique_sdk.cli.config."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

import unique_sdk
from unique_sdk.cli.config import Config, load_config


class TestConfig:
    def test_config_stores_values(self) -> None:
        c = Config(
            user_id="u1",
            company_id="c1",
            api_key="key",
            app_id="app",
            api_base="https://example.com",
        )
        assert c.user_id == "u1"
        assert c.company_id == "c1"
        assert c.api_key == "key"
        assert c.app_id == "app"
        assert c.api_base == "https://example.com"


class TestLoadConfig:
    @patch.dict(
        os.environ,
        {
            "UNIQUE_API_KEY": "ukey_test",
            "UNIQUE_APP_ID": "app_test",
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
        },
        clear=False,
    )
    def test_loads_from_env(self) -> None:
        config = load_config()
        assert config.api_key == "ukey_test"
        assert config.app_id == "app_test"
        assert config.user_id == "user_test"
        assert config.company_id == "company_test"
        assert unique_sdk.api_key == "ukey_test"
        assert unique_sdk.app_id == "app_test"

    @patch.dict(
        os.environ,
        {
            "UNIQUE_API_KEY": "ukey_test",
            "UNIQUE_APP_ID": "app_test",
            "UNIQUE_USER_ID": "user_test",
            "UNIQUE_COMPANY_ID": "company_test",
            "UNIQUE_API_BASE": "https://custom.example.com",
        },
        clear=False,
    )
    def test_custom_api_base(self) -> None:
        config = load_config()
        assert config.api_base == "https://custom.example.com"
        assert unique_sdk.api_base == "https://custom.example.com"

    @patch.dict(
        os.environ,
        {"UNIQUE_API_KEY": "ukey_test"},
        clear=True,
    )
    def test_missing_vars_exits(self) -> None:
        with pytest.raises(SystemExit):
            load_config()

    @patch.dict(os.environ, {}, clear=True)
    def test_all_vars_missing_exits(self) -> None:
        with pytest.raises(SystemExit):
            load_config()
