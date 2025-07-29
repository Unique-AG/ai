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


def test_missing_required_env_vars(monkeypatch):
    # Clear relevant environment variables
    for key in ["UNIQUE_AUTH_COMPANY_ID", "UNIQUE_AUTH_USER_ID"]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError):
        UniqueSettings.from_env()


def test_invalid_env_file_path():
    with pytest.raises(FileNotFoundError):
        UniqueSettings.from_env(env_file=Path("/nonexistent/.env"))
