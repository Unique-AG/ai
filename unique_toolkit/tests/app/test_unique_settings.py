import logging
from pathlib import Path

import pytest

from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueChatEventFilterOptions,
    UniqueSettings,
)


def test_direct_initialization(base_unique_settings: UniqueSettings):
    """Test direct initialization using base fixture."""
    settings = base_unique_settings

    assert settings.auth.company_id.get_secret_value() == "test-company"
    assert settings.auth.user_id.get_secret_value() == "test-user"
    assert settings.app.id.get_secret_value() == "test-id"
    assert settings.app.base_url == "https://api.example.com"
    assert settings.api.base_url == "https://api.example.com"
    assert settings.api.version == "2023-12-06"


def test_from_env_initialization(monkeypatch, prefixed_env_vars):
    """Test initialization from prefixed environment variables."""
    for key, value in prefixed_env_vars.items():
        monkeypatch.setenv(key, value)

    settings = UniqueSettings.from_env()

    assert settings.auth.company_id.get_secret_value() == "prefixed-company"
    assert settings.auth.user_id.get_secret_value() == "prefixed-user"
    assert settings.app.id.get_secret_value() == "prefixed-id"
    assert settings.app.base_url == "https://prefixed.api.example.com"


def test_legacy_env_variables(monkeypatch, legacy_env_vars):
    """Test that legacy environment variable names work correctly."""
    for key, value in legacy_env_vars.items():
        monkeypatch.setenv(key, value)

    settings = UniqueSettings.from_env()

    assert settings.api.base_url == "https://legacy.api.example.com"
    assert settings.api.version == "2024-01-01"
    assert settings.auth.company_id.get_secret_value() == "legacy-company"
    assert settings.auth.user_id.get_secret_value() == "legacy-user"
    assert settings.app.id.get_secret_value() == "legacy-app-id"
    assert settings.app.key.get_secret_value() == "legacy-app-key"


def test_api_key_legacy_aliases(monkeypatch, app_key_aliases):
    """Test that all app key aliases work correctly."""
    for alias in app_key_aliases:
        # Clear any existing environment variables
        for other_alias in app_key_aliases:
            monkeypatch.delenv(other_alias, raising=False)

        monkeypatch.setenv(alias, f"{alias.lower()}-value")
        settings = UniqueSettings.from_env()
        assert settings.app.key.get_secret_value() == f"{alias.lower()}-value"


def test_env_priority_over_legacy(monkeypatch, prefixed_env_vars, legacy_env_vars):
    """Test that prefixed environment variables take priority over legacy ones."""
    # Set both prefixed and legacy environment variables
    all_env_vars = {**prefixed_env_vars, **legacy_env_vars}

    for key, value in all_env_vars.items():
        monkeypatch.setenv(key, value)

    settings = UniqueSettings.from_env()

    # Prefixed variables should take priority
    assert settings.api.base_url == "https://prefixed.api.example.com"
    assert settings.api.version == "2024-02-01"
    assert settings.auth.company_id.get_secret_value() == "prefixed-company"
    assert settings.app.id.get_secret_value() == "prefixed-id"
    assert settings.app.key.get_secret_value() == "prefixed-key"


def test_mixed_environment_variables(monkeypatch, mixed_env_vars):
    """Test mixed environment with some prefixed and some legacy variables."""
    for key, value in mixed_env_vars.items():
        monkeypatch.setenv(key, value)

    settings = UniqueSettings.from_env()

    assert settings.api.base_url == "https://prefixed.api.example.com"
    assert settings.api.version == "2024-01-01"  # Falls back to legacy
    assert settings.auth.company_id.get_secret_value() == "prefixed-company"
    assert (
        settings.auth.user_id.get_secret_value() == "legacy-user"
    )  # Falls back to legacy
    assert settings.app.id.get_secret_value() == "legacy-app-id"  # Falls back to legacy
    assert settings.app.key.get_secret_value() == "prefixed-app-key"


def test_case_insensitive_environment_variables(monkeypatch):
    """Test that environment variables are case-insensitive."""
    # Test with various case combinations
    env_vars = {
        "base_url": "https://lowercase.api.example.com",
        "VERSION": "2024-UPPER",
        "Company_Id": "MixedCase-Company",
        "user_ID": "MixedCase-User",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    settings = UniqueSettings.from_env()

    assert settings.api.base_url == "https://lowercase.api.example.com"
    assert settings.api.version == "2024-UPPER"
    assert settings.auth.company_id.get_secret_value() == "MixedCase-Company"
    assert settings.auth.user_id.get_secret_value() == "MixedCase-User"


def test_from_env_file(tmp_path: Path, env_file_content_prefixed):
    """Test initialization from .env file with prefixed variables."""
    env_file = tmp_path / ".env"
    env_file.write_text(env_file_content_prefixed)

    settings = UniqueSettings.from_env(env_file=env_file)

    assert settings.auth.company_id.get_secret_value() == "file-company"
    assert settings.auth.user_id.get_secret_value() == "file-user"
    assert settings.app.id.get_secret_value() == "file-id"
    assert settings.api.base_url == "https://api.file-example.com"
    assert settings.api.version == "2023-12-06"


def test_legacy_env_file(tmp_path: Path, env_file_content_legacy):
    """Test that legacy environment variable names work in .env files."""
    env_file = tmp_path / ".env"
    env_file.write_text(env_file_content_legacy)

    settings = UniqueSettings.from_env(env_file=env_file)

    assert settings.api.base_url == "https://legacy-file.api.example.com"
    assert settings.api.version == "2024-03-01"
    assert settings.auth.company_id.get_secret_value() == "legacy-file-company"
    assert settings.auth.user_id.get_secret_value() == "legacy-file-user"
    assert settings.app.id.get_secret_value() == "legacy-file-app-id"
    assert settings.app.key.get_secret_value() == "legacy-file-api-key"


def test_mixed_env_file(tmp_path: Path, env_file_content_mixed):
    """Test .env file with mixed prefixed and legacy variable names."""
    env_file = tmp_path / ".env"
    env_file.write_text(env_file_content_mixed)

    settings = UniqueSettings.from_env(env_file=env_file)

    assert settings.api.base_url == "https://prefixed-file.api.example.com"
    assert settings.api.version == "2024-legacy-version"
    assert settings.auth.company_id.get_secret_value() == "prefixed-file-company"
    assert settings.auth.user_id.get_secret_value() == "legacy-file-user"
    assert settings.app.id.get_secret_value() == "legacy-file-app-id"
    assert settings.app.key.get_secret_value() == "prefixed-file-app-key"


def test_environment_overrides_env_file(tmp_path: Path, monkeypatch):
    """Test that environment variables override .env file values."""
    # Create .env file with one set of values
    env_file = tmp_path / ".env"
    env_content = """
BASE_URL=https://file.api.example.com
VERSION=2024-file-version
COMPANY_ID=file-company
"""
    env_file.write_text(env_content)

    # Set environment variables that should override
    monkeypatch.setenv("BASE_URL", "https://env.api.example.com")
    monkeypatch.setenv("VERSION", "2024-env-version")
    # Leave COMPANY_ID unset to test fallback to file

    settings = UniqueSettings.from_env(env_file=env_file)

    assert settings.api.base_url == "https://env.api.example.com"  # From env
    assert settings.api.version == "2024-env-version"  # From env
    assert settings.auth.company_id.get_secret_value() == "file-company"  # From file


def test_invalid_env_file_path():
    with pytest.raises(FileNotFoundError):
        UniqueSettings.from_env(env_file=Path("/nonexistent/.env"))


def test_nonexistent_env_file_none():
    """Test that passing None for env_file works correctly."""
    settings = UniqueSettings.from_env(env_file=None)
    # Should use default values since no env vars are set
    assert settings.api.base_url == "http://localhost:8092/"
    assert settings.api.version == "2023-12-06"


def test_all_alias_combinations(
    monkeypatch, base_url_aliases, app_key_aliases, app_id_aliases
):
    """Test that all defined aliases work for each field."""
    # Test all aliases for base_url
    for alias in base_url_aliases:
        monkeypatch.delenv(alias, raising=False)  # Clear any existing
        monkeypatch.setenv(alias, f"https://{alias.lower()}.example.com")
        settings = UniqueSettings.from_env()
        assert settings.api.base_url == f"https://{alias.lower()}.example.com"
        monkeypatch.delenv(alias)

    # Test all aliases for app key
    for alias in app_key_aliases:
        for other_alias in app_key_aliases:
            monkeypatch.delenv(other_alias, raising=False)  # Clear all others
        monkeypatch.setenv(alias, f"{alias.lower()}-value")
        settings = UniqueSettings.from_env()
        assert settings.app.key.get_secret_value() == f"{alias.lower()}-value"
        monkeypatch.delenv(alias)

    # Test all aliases for app id
    for alias in app_id_aliases:
        for other_alias in app_id_aliases:
            monkeypatch.delenv(other_alias, raising=False)  # Clear all others
        monkeypatch.setenv(alias, f"{alias.lower()}-id-value")
        settings = UniqueSettings.from_env()
        assert settings.app.id.get_secret_value() == f"{alias.lower()}-id-value"
        monkeypatch.delenv(alias)


def test_default_values_reported(caplog):
    with caplog.at_level(logging.WARNING):
        UniqueApp()
        UniqueApi()
        UniqueAuth()

    assert "Using default value for 'id':" in caplog.text
    assert "Using default value for 'key':" in caplog.text
    assert "Using default value for 'base_url':" in caplog.text
    assert "Using default value for 'endpoint':" in caplog.text
    assert "Using default value for 'endpoint_secret':" in caplog.text
    assert "Using default value for 'base_url':" in caplog.text
    assert "Using default value for 'version':" in caplog.text
    assert "Using default value for 'company_id':" in caplog.text
    assert "Using default value for 'user_id':" in caplog.text


class TestUniqueChatEventFilterOptions:
    def test_default_initialization(self, base_chat_event_filter_options):
        """Test that UniqueChatEventFilterOptions initializes with empty lists by default."""
        filter_options = base_chat_event_filter_options

        assert filter_options.assistant_ids == []
        assert filter_options.references_in_code == []

    def test_custom_initialization(self):
        """Test that UniqueChatEventFilterOptions can be initialized with custom values."""
        filter_options = UniqueChatEventFilterOptions(
            assistant_ids=["assistant1", "assistant2"],
            references_in_code=["module1", "module2"],
        )

        assert filter_options.assistant_ids == ["assistant1", "assistant2"]
        assert filter_options.references_in_code == ["module1", "module2"]

    def test_from_env_variables(self, monkeypatch, filter_options_env_vars):
        """Test that UniqueChatEventFilterOptions can be loaded from environment variables."""
        for key, value in filter_options_env_vars.items():
            monkeypatch.setenv(key, value)

        filter_options = UniqueChatEventFilterOptions()

        assert filter_options.assistant_ids == ["assistant1", "assistant2"]
        assert filter_options.references_in_code == ["module1", "module2"]

    def test_case_insensitive_env_variables(self, monkeypatch):
        """Test that environment variables are case-insensitive."""
        monkeypatch.setenv(
            "UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS", '["assistant1"]'
        )
        monkeypatch.setenv(
            "UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE", '["module1"]'
        )

        filter_options = UniqueChatEventFilterOptions()

        assert filter_options.assistant_ids == ["assistant1"]
        assert filter_options.references_in_code == ["module1"]

    def test_empty_string_handling(self, monkeypatch):
        """Test that empty strings are handled correctly."""
        monkeypatch.setenv("UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS", "[]")
        monkeypatch.setenv("UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE", "[]")

        filter_options = UniqueChatEventFilterOptions()

        # Empty JSON arrays should result in empty lists
        assert filter_options.assistant_ids == []
        assert filter_options.references_in_code == []

    def test_whitespace_string_handling(self, monkeypatch):
        """Test that whitespace strings are handled correctly."""
        monkeypatch.setenv("UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS", "[]")
        monkeypatch.setenv("UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE", "[]")

        filter_options = UniqueChatEventFilterOptions()

        # Empty JSON arrays should result in empty lists
        assert filter_options.assistant_ids == []
        assert filter_options.references_in_code == []


class TestUniqueSettingsWithFilterOptions:
    def test_from_env_with_filter_options(
        self, monkeypatch, prefixed_env_vars, filter_options_env_vars
    ):
        """Test that UniqueSettings.from_env loads filter options from environment."""
        # Set basic required environment variables
        all_env_vars = {**prefixed_env_vars, **filter_options_env_vars}

        for key, value in all_env_vars.items():
            monkeypatch.setenv(key, value)

        settings = UniqueSettings.from_env()

        assert settings.chat_event_filter_options is not None
        assert settings.chat_event_filter_options.assistant_ids == [
            "assistant1",
            "assistant2",
        ]
        assert settings.chat_event_filter_options.references_in_code == [
            "module1",
            "module2",
        ]

    def test_from_env_without_filter_options(self, monkeypatch, prefixed_env_vars):
        """Test that UniqueSettings.from_env works without filter options."""
        for key, value in prefixed_env_vars.items():
            monkeypatch.setenv(key, value)

        settings = UniqueSettings.from_env()

        # Should still create filter options with default values
        assert settings.chat_event_filter_options is not None
        assert settings.chat_event_filter_options.assistant_ids == []
        assert settings.chat_event_filter_options.references_in_code == []

    def test_from_env_file_with_filter_options(
        self, tmp_path, env_file_content_with_filters
    ):
        """Test that UniqueSettings.from_env loads filter options from env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(env_file_content_with_filters)

        settings = UniqueSettings.from_env(env_file=env_file)

        assert settings.chat_event_filter_options is not None
        assert settings.chat_event_filter_options.assistant_ids == [
            "file-assistant1",
            "file-assistant2",
        ]
        assert settings.chat_event_filter_options.references_in_code == [
            "file-module1",
            "file-module2",
        ]
