import logging
from pathlib import Path

import pytest
from pydantic import SecretStr

from unique_toolkit.app.schemas import (
    BaseEvent,
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    Correlation,
    EventName,
)
from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    EnvFileNotFoundError,
    UniqueApi,
    UniqueApp,
    UniqueAuth,
    UniqueChatEventFilterOptions,
    UniqueContext,
    UniqueSettings,
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
        ("my-service.default.svc.cluster", "/public"),
        ("my-service.default.svc", "/public"),
    ],
    ids=[
        "qa-gateway",
        "prod-gateway",
        "localhost",
        "cluster-local",
        "svc-dot-in-hostname",
        "hostname-ends-with-svc",
    ],
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
    # Assert (deprecated settings.auth must still work after update_from_event)
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
    assert settings.chat_event_filter_options is not None
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
def test_unique_settings__with_auth__returns_distinct_instance__with_new_auth(
    valid_auth: UniqueAuth, valid_app: UniqueApp, valid_api: UniqueApi
) -> None:
    """Branch settings with a new AuthContext; app/api shared, original auth unchanged."""
    settings = UniqueSettings(auth=valid_auth, app=valid_app, api=valid_api)
    new_auth = AuthContext(
        company_id=SecretStr("branch-co"), user_id=SecretStr("branch-user")
    )
    branched = settings.with_auth(new_auth)
    assert branched is not settings
    assert branched.authcontext is new_auth
    assert branched.authcontext.get_confidential_company_id() == "branch-co"
    assert branched.authcontext.get_confidential_user_id() == "branch-user"
    assert settings.authcontext is valid_auth
    assert branched.app is valid_app
    assert branched.api is valid_api
    assert branched.context.chat is None


@pytest.mark.ai
def test_unique_settings__with_auth__preserves_chat_filters_and_env_file(
    valid_auth: UniqueAuth,
    valid_app: UniqueApp,
    valid_api: UniqueApi,
    tmp_path: Path,
) -> None:
    """with_auth keeps chat, filter options, and stored env file path on the clone."""
    env_file = tmp_path / "branch.env"
    env_file.write_text("FOO=bar")
    chat = ChatContext(chat_id="chat-z", assistant_id="asst-z")
    filters = UniqueChatEventFilterOptions(
        assistant_ids=["a1"], references_in_code=["m1"]
    )
    settings = UniqueSettings(
        auth=valid_auth,
        app=valid_app,
        api=valid_api,
        chat_event_filter_options=filters,
        chat=chat,
        env_file=env_file,
    )
    new_auth = AuthContext(
        company_id=SecretStr("other-co"), user_id=SecretStr("other-user")
    )
    branched = settings.with_auth(new_auth)
    assert branched.authcontext is new_auth
    assert branched.context.chat is chat
    assert branched.chat_event_filter_options is filters
    assert branched._env_file == env_file


@pytest.mark.ai
def test_env_file_not_found_error__is_file_not_found_error() -> None:
    """
    Purpose: Verify EnvFileNotFoundError is a subclass of FileNotFoundError.
    Why this matters: Ensures proper exception hierarchy for error handling.
    Setup summary: Assert EnvFileNotFoundError inheritance.
    """
    # Assert
    assert issubclass(EnvFileNotFoundError, FileNotFoundError)


# ---------------------------------------------------------------------------
# Tests: AuthContext, ChatContext, UniqueContext
# ---------------------------------------------------------------------------


def _make_chat_event(
    *,
    user_id: str = "user-1",
    company_id: str = "company-1",
    chat_id: str = "chat-1",
    assistant_id: str = "asst-1",
    user_message_id: str = "umsg-1",
    assistant_message_id: str = "amsg-1",
    metadata_filter: dict | None = None,
    correlation: Correlation | None = None,
) -> ChatEvent:
    return ChatEvent(
        id="evt-1",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        user_id=user_id,
        company_id=company_id,
        payload=ChatEventPayload(
            assistant_id=assistant_id,
            chat_id=chat_id,
            name="module",
            description="desc",
            configuration={},
            user_message=ChatEventUserMessage(
                id=user_message_id,
                text="hi",
                created_at="2021-01-01T00:00:00Z",
                language="EN",
                original_text="hi",
            ),
            assistant_message=ChatEventAssistantMessage(
                id=assistant_message_id,
                created_at="2021-01-01T00:00:00Z",
            ),
            metadata_filter=metadata_filter,
            correlation=correlation,
        ),
    )


class TestAuthContext:
    @pytest.mark.ai
    def test_get_confidential_company_id__returns_plain_string(self) -> None:
        """
        Purpose: Verify get_confidential_company_id unwraps the SecretStr value.
        Why this matters: API calls need the raw string; a SecretStr repr would break requests.
        Setup summary: AuthContext with company-abc; assert plain string returned.
        """
        auth = AuthContext(
            company_id=SecretStr("company-abc"), user_id=SecretStr("user-xyz")
        )
        assert auth.get_confidential_company_id() == "company-abc"

    @pytest.mark.ai
    def test_get_confidential_user_id__returns_plain_string(self) -> None:
        """
        Purpose: Verify get_confidential_user_id unwraps the SecretStr value.
        Why this matters: API calls need the raw string; a SecretStr repr would break requests.
        Setup summary: AuthContext with user-xyz; assert plain string returned.
        """
        auth = AuthContext(
            company_id=SecretStr("company-abc"), user_id=SecretStr("user-xyz")
        )
        assert auth.get_confidential_user_id() == "user-xyz"


class TestUniqueContext:
    @pytest.mark.ai
    def test_auth__raises_value_error__when_not_set(self) -> None:
        """
        Purpose: Verify accessing .auth raises ValueError when auth was not provided.
        Why this matters: Unguarded access to a None auth would cause AttributeError deep in service code.
        Setup summary: UniqueContext(auth=None); assert ValueError on .auth access.
        """
        ctx = UniqueContext(auth=None)
        with pytest.raises(ValueError, match="Auth context not set"):
            ctx.auth  # noqa: B018

    @pytest.mark.ai
    def test_chat__is_none__when_not_provided(self) -> None:
        """
        Purpose: Verify .chat returns None when constructed without a chat context.
        Why this matters: Auth-only contexts are valid (e.g. background jobs); code must handle None chat.
        Setup summary: UniqueContext with auth only; assert ctx.chat is None.
        """
        ctx = UniqueContext(
            auth=AuthContext(company_id=SecretStr("c"), user_id=SecretStr("u"))
        )
        assert ctx.chat is None

    @pytest.mark.ai
    def test_from_chat_event__maps_company_id(self) -> None:
        """
        Purpose: Verify company_id is extracted from the event and stored in auth.
        Why this matters: Wrong company_id silently routes requests to another tenant.
        Setup summary: Event with company-42; assert auth.company_id matches.
        """
        ctx = UniqueContext.from_chat_event(_make_chat_event(company_id="company-42"))
        assert ctx.auth.get_confidential_company_id() == "company-42"

    @pytest.mark.ai
    def test_from_chat_event__maps_user_id(self) -> None:
        """
        Purpose: Verify user_id is extracted from the event and stored in auth.
        Why this matters: Wrong user_id attributes actions to the wrong user.
        Setup summary: Event with user-42; assert auth.user_id matches.
        """
        ctx = UniqueContext.from_chat_event(_make_chat_event(user_id="user-42"))
        assert ctx.auth.get_confidential_user_id() == "user-42"

    @pytest.mark.ai
    def test_from_chat_event__maps_chat_id(self) -> None:
        """
        Purpose: Verify chat_id is mapped from the event payload into the chat context.
        Why this matters: chat_id scopes all message operations; a mismatch corrupts the session.
        Setup summary: Event with chat_id="chat-99"; assert ctx.chat.chat_id matches.
        """
        ctx = UniqueContext.from_chat_event(_make_chat_event(chat_id="chat-99"))
        assert ctx.chat is not None
        assert ctx.chat.chat_id == "chat-99"

    @pytest.mark.ai
    def test_from_chat_event__maps_assistant_id(self) -> None:
        """
        Purpose: Verify assistant_id is mapped into the chat context.
        Why this matters: Replies are routed by assistant_id; a wrong value sends them to the wrong assistant.
        Setup summary: Event with assistant_id="asst-99"; assert ctx.chat.assistant_id matches.
        """
        ctx = UniqueContext.from_chat_event(_make_chat_event(assistant_id="asst-99"))
        assert ctx.chat is not None
        assert ctx.chat.assistant_id == "asst-99"

    @pytest.mark.ai
    def test_from_chat_event__maps_last_assistant_message_id(self) -> None:
        """
        Purpose: Verify last_assistant_message_id is mapped from the event's assistant message.
        Why this matters: Services use this to edit the in-progress assistant message; wrong id corrupts the reply.
        Setup summary: Event with assistant_message_id="amsg-99"; assert ctx.chat.last_assistant_message_id matches.
        """
        ctx = UniqueContext.from_chat_event(
            _make_chat_event(assistant_message_id="amsg-99")
        )
        assert ctx.chat is not None
        assert ctx.chat.last_assistant_message_id == "amsg-99"

    @pytest.mark.ai
    def test_from_chat_event__maps_user_message_id(self) -> None:
        """
        Purpose: Verify last_user_message_id is mapped from the event's user message.
        Why this matters: Services reference the user message for debug info and elicitation; wrong id causes silent failures.
        Setup summary: Event with user_message_id="umsg-99"; assert ctx.chat.last_user_message_id matches.
        """
        ctx = UniqueContext.from_chat_event(_make_chat_event(user_message_id="umsg-99"))
        assert ctx.chat is not None
        assert ctx.chat.last_user_message_id == "umsg-99"

    @pytest.mark.ai
    def test_from_chat_event__maps_metadata_filter(self) -> None:
        """
        Purpose: Verify metadata_filter is carried from the event payload into the chat context.
        Why this matters: Content search scope depends on this filter; a missing filter returns unscoped results.
        Setup summary: Event with metadata_filter={"tier": "gold"}; assert ctx.chat.metadata_filter matches.
        """
        ctx = UniqueContext.from_chat_event(
            _make_chat_event(metadata_filter={"tier": "gold"})
        )
        assert ctx.chat is not None
        assert ctx.chat.metadata_filter == {"tier": "gold"}

    @pytest.mark.ai
    def test_from_chat_event__sets_parent_chat_id__from_correlation(self) -> None:
        """
        Purpose: Verify parent_chat_id is set from correlation when the event is a subagent event.
        Why this matters: Subagent content search must be scoped to the parent session's uploads.
        Setup summary: Event with correlation.parent_chat_id="parent-chat-1"; assert ctx.chat.parent_chat_id matches.
        """
        correlation = Correlation(
            parent_chat_id="parent-chat-1",
            parent_message_id="parent-msg-1",
            parent_assistant_id="parent-asst-1",
        )
        ctx = UniqueContext.from_chat_event(_make_chat_event(correlation=correlation))
        assert ctx.chat is not None
        assert ctx.chat.parent_chat_id == "parent-chat-1"

    @pytest.mark.ai
    def test_from_chat_event__sets_parent_chat_id_none__when_no_correlation(
        self,
    ) -> None:
        """
        Purpose: Verify parent_chat_id is None when no correlation is present.
        Why this matters: Non-subagent sessions should not inherit a parent scope.
        Setup summary: Event with correlation=None; assert ctx.chat.parent_chat_id is None.
        """
        ctx = UniqueContext.from_chat_event(_make_chat_event(correlation=None))
        assert ctx.chat is not None
        assert ctx.chat.parent_chat_id is None

    @pytest.mark.ai
    def test_from_base_event__sets_auth_fields(self) -> None:
        """
        Purpose: Verify from_event maps company_id and user_id into auth.
        Why this matters: Non-chat events still need a valid auth context for API calls.
        Setup summary: BaseEvent with company-base/user-base; assert both auth fields match.
        """
        event = BaseEvent(
            id="evt-1",
            event=EventName.EXTERNAL_MODULE_CHOSEN,
            user_id="user-base",
            company_id="company-base",
        )
        ctx = UniqueContext.from_event(event)
        assert ctx.auth.get_confidential_company_id() == "company-base"
        assert ctx.auth.get_confidential_user_id() == "user-base"

    @pytest.mark.ai
    def test_from_base_event__chat_is_none(self) -> None:
        """
        Purpose: Verify from_event produces an auth-only context with no chat.
        Why this matters: BaseEvents have no chat payload; code must handle ctx.chat being None.
        Setup summary: BaseEvent; assert ctx.chat is None.
        """
        event = BaseEvent(
            id="evt-1",
            event=EventName.EXTERNAL_MODULE_CHOSEN,
            user_id="user-1",
            company_id="company-1",
        )
        ctx = UniqueContext.from_event(event)
        assert ctx.chat is None
