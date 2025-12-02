import logging
from pathlib import Path

import pytest
from pydantic import SecretStr

from unique_toolkit.app.schemas import BaseEvent
from unique_toolkit.app.unique_settings import (
    EnvFileNotFoundError,
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueChatEventFilterOptions,
    UniqueSettings,
    _find_env_file,
    warn_about_defaults,
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


class TestUniqueChatEventFilterOptions:
    def test_default_initialization(self):
        """Test that UniqueChatEventFilterOptions initializes with empty lists by default."""
        filter_options = UniqueChatEventFilterOptions()

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

    def test_from_env_variables(self, monkeypatch):
        """Test that UniqueChatEventFilterOptions can be loaded from environment variables."""
        monkeypatch.setenv(
            "UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS",
            '["assistant1", "assistant2"]',
        )
        monkeypatch.setenv(
            "UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE",
            '["module1", "module2"]',
        )

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
    def test_from_env_with_filter_options(self, monkeypatch):
        """Test that UniqueSettings.from_env loads filter options from environment."""
        # Set basic required environment variables
        env_vars = {
            "UNIQUE_AUTH_COMPANY_ID": "test-company",
            "UNIQUE_AUTH_USER_ID": "test-user",
            "UNIQUE_APP_ID": "test-id",
            "UNIQUE_APP_KEY": "test-key",
            "UNIQUE_APP_BASE_URL": "https://api.example.com",
            "UNIQUE_APP_ENDPOINT": "/v1/endpoint",
            "UNIQUE_APP_ENDPOINT_SECRET": "test-endpoint-secret",
            # Filter options
            "UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS": '["assistant1", "assistant2"]',
            "UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE": '["module1", "module2"]',
        }

        for key, value in env_vars.items():
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

    def test_from_env_without_filter_options(self, monkeypatch):
        """Test that UniqueSettings.from_env works without filter options."""
        # Set basic required environment variables
        env_vars = {
            "UNIQUE_AUTH_COMPANY_ID": "test-company",
            "UNIQUE_AUTH_USER_ID": "test-user",
            "UNIQUE_APP_ID": "test-id",
            "UNIQUE_APP_KEY": "test-key",
            "UNIQUE_APP_BASE_URL": "https://api.example.com",
            "UNIQUE_APP_ENDPOINT": "/v1/endpoint",
            "UNIQUE_APP_ENDPOINT_SECRET": "test-endpoint-secret",
        }

        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        settings = UniqueSettings.from_env()

        # Should still create filter options with default values
        assert settings.chat_event_filter_options is not None
        assert settings.chat_event_filter_options.assistant_ids == []
        assert settings.chat_event_filter_options.references_in_code == []

    def test_from_env_file_with_filter_options(self, tmp_path):
        """Test that UniqueSettings.from_env loads filter options from env file."""
        env_file = tmp_path / ".env"
        env_content = """
UNIQUE_AUTH_COMPANY_ID=file-company
UNIQUE_AUTH_USER_ID=file-user
UNIQUE_APP_ID=file-id
UNIQUE_APP_KEY=file-key
UNIQUE_APP_BASE_URL=https://api.file-example.com
UNIQUE_APP_ENDPOINT=/v1/file-endpoint
UNIQUE_APP_ENDPOINT_SECRET=file-endpoint-secret
UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS=["file-assistant1", "file-assistant2"]
UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE=["file-module1", "file-module2"]
"""
        env_file.write_text(env_content)

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


# AI-authored tests following test_instructions.md guidelines


@pytest.mark.ai
def test_warn_about_defaults__logs_warnings__with_secretstr_defaults(caplog) -> None:
    """
    Purpose: Verify warn_about_defaults logs warnings for SecretStr fields using defaults.
    Why this matters: Ensures users are aware when default values are being used for sensitive fields.
    Setup summary: Create UniqueApp with defaults, verify warning messages are logged.
    """
    # Arrange
    with caplog.at_level(logging.WARNING):
        # Act
        UniqueApp()
        # Assert
        assert "Using default value for 'id':" in caplog.text
        assert "Using default value for 'key':" in caplog.text


@pytest.mark.ai
def test_warn_about_defaults__logs_warnings__with_string_defaults(caplog) -> None:
    """
    Purpose: Verify warn_about_defaults logs warnings for string fields using defaults.
    Why this matters: Ensures users are aware when default values are being used.
    Setup summary: Create UniqueApi with defaults, verify warning messages are logged.
    """
    # Arrange
    with caplog.at_level(logging.WARNING):
        # Act
        UniqueApi()
        # Assert
        assert "Using default value for 'base_url':" in caplog.text
        assert "Using default value for 'version':" in caplog.text


@pytest.mark.ai
def test_warn_about_defaults__returns_instance__with_custom_values() -> None:
    """
    Purpose: Verify warn_about_defaults returns the instance unchanged.
    Why this matters: Ensures the function doesn't modify the instance.
    Setup summary: Create UniqueAuth with custom values, verify instance is returned unchanged.
    """
    # Arrange
    auth = UniqueAuth(
        company_id=SecretStr("custom-company"), user_id=SecretStr("custom-user")
    )
    # Act
    result = warn_about_defaults(auth)
    # Assert
    assert result is auth
    assert result.company_id.get_secret_value() == "custom-company"


@pytest.mark.ai
@pytest.mark.parametrize(
    "subscriptions,expected_query",
    [
        (["event1"], "subscriptions=event1"),
        (["event1", "event2"], "subscriptions=event1,event2"),
        ([], "subscriptions="),
    ],
    ids=["single", "multiple", "empty"],
)
def test_unique_api__sse_url__builds_correct_url(
    subscriptions: list[str], expected_query: str
) -> None:
    """
    Purpose: Verify sse_url constructs correct SSE endpoint URL with subscriptions query parameter.
    Why this matters: Ensures proper SSE connection setup for event streaming.
    Setup summary: Create UniqueApi instance, test with various subscription lists, assert URL format.
    """
    # Arrange
    api = UniqueApi(base_url="https://api.example.com/")
    # Act
    url = api.sse_url(subscriptions)
    # Assert
    assert url.startswith("https://api.example.com")
    assert "/public/event-socket/events/stream" in url
    assert expected_query in url


@pytest.mark.ai
def test_unique_api__base_path__returns_default_path__for_standard_hostname() -> None:
    """
    Purpose: Verify base_path returns default /public/chat for standard hostnames.
    Why this matters: Ensures correct API path selection for standard deployments.
    Setup summary: Create UniqueApi with standard hostname, assert default path.
    """
    # Arrange
    api = UniqueApi(base_url="https://api.example.com/")
    # Act
    parsed, base_path = api.base_path()
    # Assert
    assert base_path == "/public/chat"
    assert parsed.hostname == "api.example.com"


@pytest.mark.ai
@pytest.mark.parametrize(
    "hostname,expected_path",
    [
        ("gateway.qa.unique.com", "/public/chat-gen2"),
        ("gateway.unique.com", "/public/chat-gen2"),
        ("localhost", "/public"),
        ("svc.cluster.local", "/public"),
    ],
    ids=["qa-gateway", "prod-gateway", "localhost", "cluster-local"],
)
def test_unique_api__base_path__returns_special_path__for_special_hostnames(
    hostname: str, expected_path: str
) -> None:
    """
    Purpose: Verify base_path returns correct path based on hostname patterns.
    Why this matters: Ensures correct API path selection for different deployment environments.
    Setup summary: Create UniqueApi with special hostnames, assert correct path returned.
    """
    # Arrange
    api = UniqueApi(base_url=f"https://{hostname}/")
    # Act
    _, base_path = api.base_path()
    # Assert
    assert base_path == expected_path


@pytest.mark.ai
def test_unique_api__sdk_url__constructs_url__with_base_path() -> None:
    """
    Purpose: Verify sdk_url constructs correct SDK URL using base_path.
    Why this matters: Ensures proper SDK endpoint configuration.
    Setup summary: Create UniqueApi, call sdk_url, assert correct URL format.
    """
    # Arrange
    api = UniqueApi(base_url="https://api.example.com/")
    # Act
    url = api.sdk_url()
    # Assert
    assert url == "https://api.example.com/public/chat"
    assert not url.endswith("/")


@pytest.mark.ai
def test_unique_api__sdk_url__uses_gen2_path__for_gateway_hostname() -> None:
    """
    Purpose: Verify sdk_url uses gen2 path for gateway hostnames.
    Why this matters: Ensures correct SDK endpoint for gateway deployments.
    Setup summary: Create UniqueApi with gateway hostname, assert gen2 path in URL.
    """
    # Arrange
    api = UniqueApi(base_url="https://gateway.unique.com/")
    # Act
    url = api.sdk_url()
    # Assert
    assert url == "https://gateway.unique.com/public/chat-gen2"


@pytest.mark.ai
def test_unique_api__openai_proxy_url__constructs_url__with_openai_proxy_suffix() -> (
    None
):
    """
    Purpose: Verify openai_proxy_url constructs correct OpenAI proxy endpoint URL.
    Why this matters: Ensures proper OpenAI proxy configuration.
    Setup summary: Create UniqueApi, call openai_proxy_url, assert correct URL format.
    """
    # Arrange
    api = UniqueApi(base_url="https://api.example.com/")
    # Act
    url = api.openai_proxy_url()
    # Assert
    assert url == "https://api.example.com/public/chat/openai-proxy"


@pytest.mark.ai
def test_unique_api__openai_proxy_url__uses_gen2_path__for_gateway_hostname() -> None:
    """
    Purpose: Verify openai_proxy_url uses gen2 path for gateway hostnames.
    Why this matters: Ensures correct OpenAI proxy endpoint for gateway deployments.
    Setup summary: Create UniqueApi with gateway hostname, assert gen2 path in URL.
    """
    # Arrange
    api = UniqueApi(base_url="https://gateway.unique.com/")
    # Act
    url = api.openai_proxy_url()
    # Assert
    assert url == "https://gateway.unique.com/public/chat-gen2/openai-proxy"


@pytest.mark.ai
def test_unique_auth__from_event__creates_auth__with_event_ids() -> None:
    """
    Purpose: Verify from_event creates UniqueAuth instance from BaseEvent.
    Why this matters: Enables authentication setup from event data.
    Setup summary: Create BaseEvent with company and user IDs, call from_event, assert correct values.
    """
    # Arrange
    event = BaseEvent(
        id="event-123",
        event="test.event",
        user_id="user-456",
        company_id="company-789",
    )
    # Act
    auth = UniqueAuth.from_event(event)
    # Assert
    assert auth.company_id.get_secret_value() == "company-789"
    assert auth.user_id.get_secret_value() == "user-456"


@pytest.mark.ai
def test_unique_settings__find_env_file__returns_path__from_env_variable(
    tmp_path: Path, monkeypatch
) -> None:
    """
    Purpose: Verify _find_env_file prioritizes UNIQUE_ENV_FILE environment variable.
    Why this matters: Ensures explicit configuration takes precedence.
    Setup summary: Set UNIQUE_ENV_FILE, create file at that path, assert it's found.
    """
    # Arrange
    env_file = tmp_path / "custom.env"
    env_file.write_text("TEST=value")
    monkeypatch.setenv("UNIQUE_ENV_FILE", str(env_file))
    # Act
    found_path = _find_env_file()
    # Assert
    assert found_path == env_file


@pytest.mark.ai
def test_unique_settings__find_env_file__returns_path__from_current_directory(
    tmp_path: Path, monkeypatch
) -> None:
    """
    Purpose: Verify _find_env_file falls back to current working directory.
    Why this matters: Ensures standard location discovery works.
    Setup summary: Remove UNIQUE_ENV_FILE, create file in cwd, assert it's found.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_ENV_FILE", raising=False)
    env_file = tmp_path / "unique.env"
    env_file.write_text("TEST=value")
    monkeypatch.chdir(tmp_path)
    # Act
    found_path = _find_env_file()
    # Assert
    assert found_path == env_file


@pytest.mark.ai
def test_unique_settings__find_env_file__raises_error__when_not_found(
    tmp_path: Path, monkeypatch
) -> None:
    """
    Purpose: Verify _find_env_file raises EnvFileNotFoundError when file doesn't exist.
    Why this matters: Provides clear error message when configuration is missing.
    Setup summary: Remove UNIQUE_ENV_FILE, ensure no file exists, assert exception with helpful message.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_ENV_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    # Act & Assert
    with pytest.raises(EnvFileNotFoundError) as exc_info:
        _find_env_file()
    assert "not found" in str(exc_info.value)
    assert "UNIQUE_ENV_FILE" in str(exc_info.value)


@pytest.mark.ai
def test_unique_settings__from_env_auto__loads_from_file__when_found(
    tmp_path: Path, monkeypatch
) -> None:
    """
    Purpose: Verify from_env_auto loads settings from found environment file.
    Why this matters: Enables automatic configuration discovery.
    Setup summary: Create env file with settings, call from_env_auto, assert values loaded.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_ENV_FILE", raising=False)
    env_file = tmp_path / "unique.env"
    env_file.write_text(
        "UNIQUE_AUTH_COMPANY_ID=auto-company\n"
        "UNIQUE_AUTH_USER_ID=auto-user\n"
        "UNIQUE_APP_ID=auto-id\n"
        "UNIQUE_APP_KEY=auto-key\n"
    )
    monkeypatch.chdir(tmp_path)
    # Act
    settings = UniqueSettings.from_env_auto()
    # Assert
    assert settings.auth.company_id.get_secret_value() == "auto-company"
    assert settings.auth.user_id.get_secret_value() == "auto-user"


@pytest.mark.ai
def test_unique_settings__from_env_auto__falls_back_to_env__when_file_not_found(
    monkeypatch,
) -> None:
    """
    Purpose: Verify from_env_auto falls back to environment variables when file not found.
    Why this matters: Ensures graceful degradation when file doesn't exist.
    Setup summary: Ensure no env file exists, set env vars, call from_env_auto, assert values from env.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_ENV_FILE", raising=False)
    monkeypatch.setenv("UNIQUE_AUTH_COMPANY_ID", "env-company")
    monkeypatch.setenv("UNIQUE_AUTH_USER_ID", "env-user")
    # Act
    settings = UniqueSettings.from_env_auto()
    # Assert
    assert settings.auth.company_id.get_secret_value() == "env-company"
    assert settings.auth.user_id.get_secret_value() == "env-user"


@pytest.mark.ai
def test_unique_settings__init_sdk__configures_global_sdk__with_settings_values(
    valid_auth: UniqueAuth, valid_app: UniqueApp, valid_api: UniqueApi
) -> None:
    """
    Purpose: Verify init_sdk configures unique_sdk global module with settings values.
    Why this matters: Ensures SDK is properly initialized for API calls.
    Setup summary: Create UniqueSettings, call init_sdk, assert unique_sdk globals are set.
    """
    # Arrange
    settings = UniqueSettings(auth=valid_auth, app=valid_app, api=valid_api)
    # Act
    settings.init_sdk()
    # Assert
    import unique_sdk

    assert unique_sdk.api_key == valid_app.key.get_secret_value()
    assert unique_sdk.app_id == valid_app.id.get_secret_value()
    assert unique_sdk.api_base == valid_api.sdk_url()


@pytest.mark.ai
def test_unique_settings__from_env_auto_with_sdk_init__initializes_both__in_one_call(
    tmp_path: Path, monkeypatch
) -> None:
    """
    Purpose: Verify from_env_auto_with_sdk_init combines initialization and SDK setup.
    Why this matters: Provides convenient one-call setup for common use case.
    Setup summary: Create env file, call from_env_auto_with_sdk_init, assert settings and SDK configured.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_ENV_FILE", raising=False)
    env_file = tmp_path / "unique.env"
    env_file.write_text(
        "UNIQUE_AUTH_COMPANY_ID=init-company\n"
        "UNIQUE_AUTH_USER_ID=init-user\n"
        "UNIQUE_APP_ID=init-id\n"
        "UNIQUE_APP_KEY=init-key\n"
    )
    monkeypatch.chdir(tmp_path)
    # Act
    settings = UniqueSettings.from_env_auto_with_sdk_init()
    # Assert
    import unique_sdk

    assert settings.auth.company_id.get_secret_value() == "init-company"
    assert unique_sdk.api_key == "init-key"
    assert unique_sdk.app_id == "init-id"


@pytest.mark.ai
def test_unique_settings__update_from_event__updates_auth__with_event_data(
    valid_auth: UniqueAuth, valid_app: UniqueApp, valid_api: UniqueApi
) -> None:
    """
    Purpose: Verify update_from_event updates auth settings from event.
    Why this matters: Enables dynamic authentication updates during event processing.
    Setup summary: Create UniqueSettings and BaseEvent, call update_from_event, assert auth updated.
    """
    # Arrange
    settings = UniqueSettings(auth=valid_auth, app=valid_app, api=valid_api)
    event = BaseEvent(
        id="event-123",
        event="test.event",
        user_id="new-user",
        company_id="new-company",
    )
    # Act
    settings.update_from_event(event)
    # Assert
    assert settings.auth.user_id.get_secret_value() == "new-user"
    assert settings.auth.company_id.get_secret_value() == "new-company"


@pytest.mark.ai
def test_unique_settings__properties__return_correct_values(
    valid_auth: UniqueAuth, valid_app: UniqueApp, valid_api: UniqueApi
) -> None:
    """
    Purpose: Verify UniqueSettings properties return correct component instances.
    Why this matters: Ensures proper access to configuration components.
    Setup summary: Create UniqueSettings, access properties, assert correct instances returned.
    """
    # Arrange
    settings = UniqueSettings(auth=valid_auth, app=valid_app, api=valid_api)
    # Act & Assert
    assert settings.api is valid_api
    assert settings.app is valid_app
    assert settings.auth is valid_auth


@pytest.mark.ai
def test_unique_settings__auth_setter__updates_auth__with_new_value(
    valid_auth: UniqueAuth, valid_app: UniqueApp, valid_api: UniqueApi
) -> None:
    """
    Purpose: Verify auth setter updates the auth component.
    Why this matters: Enables dynamic authentication updates.
    Setup summary: Create UniqueSettings, set new auth value, assert auth updated.
    """
    # Arrange
    settings = UniqueSettings(auth=valid_auth, app=valid_app, api=valid_api)
    new_auth = UniqueAuth(
        company_id=SecretStr("new-company"), user_id=SecretStr("new-user")
    )
    # Act
    settings.auth = new_auth
    # Assert
    assert settings.auth is new_auth
    assert settings.auth.company_id.get_secret_value() == "new-company"


@pytest.mark.ai
def test_unique_settings__chat_event_filter_options__returns_none__when_not_provided(
    valid_auth: UniqueAuth, valid_app: UniqueApp, valid_api: UniqueApi
) -> None:
    """
    Purpose: Verify chat_event_filter_options returns None when not provided.
    Why this matters: Ensures optional component handling works correctly.
    Setup summary: Create UniqueSettings without filter options, assert None returned.
    """
    # Arrange
    settings = UniqueSettings(auth=valid_auth, app=valid_app, api=valid_api)
    # Act & Assert
    assert settings.chat_event_filter_options is None


@pytest.mark.ai
def test_unique_settings__chat_event_filter_options__returns_options__when_provided(
    valid_auth: UniqueAuth,
    valid_app: UniqueApp,
    valid_api: UniqueApi,
) -> None:
    """
    Purpose: Verify chat_event_filter_options returns provided filter options.
    Why this matters: Ensures filter options are properly stored and accessible.
    Setup summary: Create UniqueSettings with filter options, assert correct instance returned.
    """
    # Arrange
    filter_options = UniqueChatEventFilterOptions(
        assistant_ids=["assistant1"], references_in_code=["module1"]
    )
    settings = UniqueSettings(
        auth=valid_auth,
        app=valid_app,
        api=valid_api,
        chat_event_filter_options=filter_options,
    )
    # Act & Assert
    assert settings.chat_event_filter_options is filter_options
    assert settings.chat_event_filter_options.assistant_ids == ["assistant1"]


@pytest.mark.ai
def test_unique_settings__init__stores_env_file__when_exists(
    valid_auth: UniqueAuth, valid_app: UniqueApp, valid_api: UniqueApi, tmp_path: Path
) -> None:
    """
    Purpose: Verify UniqueSettings stores env_file path when file exists.
    Why this matters: Enables tracking of configuration source.
    Setup summary: Create env file, initialize UniqueSettings with it, assert stored.
    """
    # Arrange
    env_file = tmp_path / "test.env"
    env_file.write_text("TEST=value")
    # Act
    settings = UniqueSettings(
        auth=valid_auth, app=valid_app, api=valid_api, env_file=env_file
    )
    # Assert
    assert settings._env_file == env_file


@pytest.mark.ai
def test_unique_settings__init__ignores_env_file__when_not_exists(
    valid_auth: UniqueAuth, valid_app: UniqueApp, valid_api: UniqueApi
) -> None:
    """
    Purpose: Verify UniqueSettings ignores env_file path when file doesn't exist.
    Why this matters: Prevents errors from non-existent file paths.
    Setup summary: Initialize UniqueSettings with non-existent path, assert None stored.
    """
    # Arrange
    non_existent_file = Path("/nonexistent/path.env")
    # Act
    settings = UniqueSettings(
        auth=valid_auth, app=valid_app, api=valid_api, env_file=non_existent_file
    )
    # Assert
    assert settings._env_file is None


@pytest.mark.ai
def test_env_file_not_found_error__is_file_not_found_error() -> None:
    """
    Purpose: Verify EnvFileNotFoundError is a subclass of FileNotFoundError.
    Why this matters: Ensures proper exception hierarchy for error handling.
    Setup summary: Assert EnvFileNotFoundError inheritance.
    """
    # Assert
    assert issubclass(EnvFileNotFoundError, FileNotFoundError)


@pytest.mark.ai
def test_unique_settings__multiple_instances__maintain_isolated_auth(
    valid_app: UniqueApp, valid_api: UniqueApi
) -> None:
    """
    Purpose: Verify that multiple UniqueSettings instances maintain their own isolated auth values.
    Why this matters: Ensures instance isolation - creating a new instance should not affect
    previously created instances' auth values.
    Setup summary: Create two instances with different auth values, verify each maintains its own.
    """
    # Arrange
    auth1 = UniqueAuth(company_id=SecretStr("company-1"), user_id=SecretStr("user-1"))
    auth2 = UniqueAuth(company_id=SecretStr("company-2"), user_id=SecretStr("user-2"))

    # Act
    settings1 = UniqueSettings(auth=auth1, app=valid_app, api=valid_api)
    settings2 = UniqueSettings(auth=auth2, app=valid_app, api=valid_api)

    # Assert - each instance should maintain its own auth
    assert settings1.auth.company_id.get_secret_value() == "company-1"
    assert settings1.auth.user_id.get_secret_value() == "user-1"
    assert settings2.auth.company_id.get_secret_value() == "company-2"
    assert settings2.auth.user_id.get_secret_value() == "user-2"

    # Verify that settings1 still has its original auth after settings2 was created
    assert settings1.auth.company_id.get_secret_value() == "company-1"
    assert settings1.auth.user_id.get_secret_value() == "user-1"
