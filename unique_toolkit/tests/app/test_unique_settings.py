import logging
from pathlib import Path

import pytest
from pydantic import SecretStr

from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueSettings,
)


@pytest.fixture
def valid_auth():
    return UniqueAuth(
        company_id=SecretStr("test-company"), user_id=SecretStr("test-user")
    )


@pytest.fixture
def valid_app():
    return UniqueApp(
        id=SecretStr("test-id"),
        key=SecretStr("test-key"),
        base_url="https://api.example.com",
        endpoint="/v1/endpoint",
        endpoint_secret=SecretStr("test-endpoint-secret"),
    )


@pytest.fixture
def valid_api():
    return UniqueApi(
        base_url="https://api.example.com",
        version="2023-12-06",
    )


def test_direct_initialization(
    valid_auth: UniqueAuth, valid_app: UniqueApp, valid_api: UniqueApi
):
    settings = UniqueSettings(auth=valid_auth, app=valid_app, api=valid_api)

    assert settings.auth == valid_auth
    assert settings.app == valid_app
    assert settings.auth.company_id.get_secret_value() == "test-company"
    assert settings.app.base_url == "https://api.example.com"


def test_from_env_initialization(monkeypatch):
    # Set environment variables
    env_vars = {
        "UNIQUE_AUTH_COMPANY_ID": "env-company",
        "UNIQUE_AUTH_USER_ID": "env-user",
        "UNIQUE_APP_ID": "env-id",
        "UNIQUE_APP_KEY": "env-key",
        "UNIQUE_APP_BASE_URL": "https://api.env-example.com",
        "UNIQUE_APP_ENDPOINT": "/v1/env-endpoint",
        "UNIQUE_APP_ENDPOINT_SECRET": "env-endpoint-secret",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    settings = UniqueSettings.from_env()

    assert settings.auth.company_id.get_secret_value() == "env-company"
    assert settings.auth.user_id.get_secret_value() == "env-user"
    assert settings.app.id.get_secret_value() == "env-id"
    assert settings.app.base_url == "https://api.env-example.com"


def test_legacy_env_variables(monkeypatch):
    """Test that legacy environment variable names work correctly."""
    # Set legacy environment variables
    legacy_env_vars = {
        "BASE_URL": "https://legacy.api.example.com",
        "VERSION": "2024-01-01",
        "COMPANY_ID": "legacy-company",
        "USER_ID": "legacy-user",
        "APP_ID": "legacy-app-id",
        "API_KEY": "legacy-app-key",
    }

    for key, value in legacy_env_vars.items():
        monkeypatch.setenv(key, value)

    settings = UniqueSettings.from_env()

    assert settings.api.base_url == "https://legacy.api.example.com"
    assert settings.api.version == "2024-01-01"
    assert settings.auth.company_id.get_secret_value() == "legacy-company"
    assert settings.auth.user_id.get_secret_value() == "legacy-user"
    assert settings.app.id.get_secret_value() == "legacy-app-id"
    assert settings.app.key.get_secret_value() == "legacy-app-key"


def test_api_key_legacy_aliases(monkeypatch):
    """Test that API_KEY and api_key work as legacy aliases for app.key."""
    test_cases = [
        ("API_KEY", "legacy-api-key-upper"),
        ("api_key", "legacy-api-key-lower"),
    ]

    for env_var, expected_value in test_cases:
        # Clear any existing environment variables
        for var in ["UNIQUE_APP_KEY", "KEY", "API_KEY", "api_key"]:
            monkeypatch.delenv(var, raising=False)

        monkeypatch.setenv(env_var, expected_value)
        settings = UniqueSettings.from_env()
        assert settings.app.key.get_secret_value() == expected_value


def test_env_priority_over_legacy(monkeypatch):
    """Test that prefixed environment variables take priority over legacy ones."""
    # Set both prefixed and legacy environment variables
    env_vars = {
        "UNIQUE_API_BASE_URL": "https://prefixed.api.example.com",
        "BASE_URL": "https://legacy.api.example.com",
        "UNIQUE_API_VERSION": "2024-02-01",
        "VERSION": "2024-01-01",
        "UNIQUE_AUTH_COMPANY_ID": "prefixed-company",
        "COMPANY_ID": "legacy-company",
        "UNIQUE_APP_ID": "prefixed-app-id",
        "APP_ID": "legacy-app-id",
        "UNIQUE_APP_KEY": "prefixed-app-key",
        "API_KEY": "legacy-api-key",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    settings = UniqueSettings.from_env()

    # Prefixed variables should take priority
    assert settings.api.base_url == "https://prefixed.api.example.com"
    assert settings.api.version == "2024-02-01"
    assert settings.auth.company_id.get_secret_value() == "prefixed-company"
    assert settings.app.id.get_secret_value() == "prefixed-app-id"
    assert settings.app.key.get_secret_value() == "prefixed-app-key"


def test_mixed_environment_variables(monkeypatch):
    """Test mixed environment with some prefixed and some legacy variables."""
    env_vars = {
        "UNIQUE_API_BASE_URL": "https://prefixed.api.example.com",  # Prefixed
        "VERSION": "2024-01-01",  # Legacy
        "UNIQUE_AUTH_COMPANY_ID": "prefixed-company",  # Prefixed
        "USER_ID": "legacy-user",  # Legacy
        "APP_ID": "legacy-app-id",  # Legacy
        "UNIQUE_APP_KEY": "prefixed-app-key",  # Prefixed
    }

    for key, value in env_vars.items():
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


def test_from_env_file(tmp_path: Path):
    # Create a temporary .env file
    env_file = tmp_path / ".env"
    env_content = """
UNIQUE_AUTH_COMPANY_ID=file-company
UNIQUE_AUTH_USER_ID=file-user
UNIQUE_APP_ID=file-id
UNIQUE_APP_KEY=file-key
UNIQUE_APP_ENDPOINT=/v1/file-endpoint
UNIQUE_APP_ENDPOINT_SECRET=file-endpoint-secret
UNIQUE_API_BASE_URL=https://api.file-example.com
UNIQUE_API_VERSION=2023-12-06
"""
    env_file.write_text(env_content)

    settings = UniqueSettings.from_env(env_file=env_file)

    assert settings.auth.company_id.get_secret_value() == "file-company"
    assert settings.auth.user_id.get_secret_value() == "file-user"
    assert settings.app.id.get_secret_value() == "file-id"
    assert settings.api.base_url == "https://api.file-example.com"
    assert settings.api.version == "2023-12-06"


def test_legacy_env_file(tmp_path: Path):
    """Test that legacy environment variable names work in .env files."""
    # Create a temporary .env file with legacy variable names
    env_file = tmp_path / ".env"
    env_content = """
BASE_URL=https://legacy-file.api.example.com
VERSION=2024-03-01
COMPANY_ID=legacy-file-company
USER_ID=legacy-file-user
APP_ID=legacy-file-app-id
API_KEY=legacy-file-api-key
"""
    env_file.write_text(env_content)

    settings = UniqueSettings.from_env(env_file=env_file)

    assert settings.api.base_url == "https://legacy-file.api.example.com"
    assert settings.api.version == "2024-03-01"
    assert settings.auth.company_id.get_secret_value() == "legacy-file-company"
    assert settings.auth.user_id.get_secret_value() == "legacy-file-user"
    assert settings.app.id.get_secret_value() == "legacy-file-app-id"
    assert settings.app.key.get_secret_value() == "legacy-file-api-key"


def test_mixed_env_file(tmp_path: Path):
    """Test .env file with mixed prefixed and legacy variable names."""
    env_file = tmp_path / ".env"
    env_content = """
UNIQUE_API_BASE_URL=https://prefixed-file.api.example.com
VERSION=2024-legacy-version
UNIQUE_AUTH_COMPANY_ID=prefixed-file-company
USER_ID=legacy-file-user
APP_ID=legacy-file-app-id
UNIQUE_APP_KEY=prefixed-file-app-key
"""
    env_file.write_text(env_content)

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


def test_all_alias_combinations(monkeypatch):
    """Test that all defined aliases work for each field."""
    # Test all aliases for base_url
    base_url_aliases = [
        "unique_api_base_url",
        "base_url",
        "UNIQUE_API_BASE_URL",
        "BASE_URL",
    ]
    for alias in base_url_aliases:
        monkeypatch.delenv(alias, raising=False)  # Clear any existing
        monkeypatch.setenv(alias, f"https://{alias.lower()}.example.com")
        settings = UniqueSettings.from_env()
        assert settings.api.base_url == f"https://{alias.lower()}.example.com"
        monkeypatch.delenv(alias)

    # Test all aliases for app key
    key_aliases = [
        "unique_app_key",
        "key",
        "UNIQUE_APP_KEY",
        "KEY",
        "API_KEY",
        "api_key",
    ]
    for alias in key_aliases:
        for other_alias in key_aliases:
            monkeypatch.delenv(other_alias, raising=False)  # Clear all others
        monkeypatch.setenv(alias, f"{alias.lower()}-value")
        settings = UniqueSettings.from_env()
        assert settings.app.key.get_secret_value() == f"{alias.lower()}-value"
        monkeypatch.delenv(alias)

    # Test all aliases for app id
    id_aliases = ["unique_app_id", "app_id", "UNIQUE_APP_ID", "APP_ID"]
    for alias in id_aliases:
        for other_alias in id_aliases:
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
