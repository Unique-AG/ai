"""Tests for ServerSettings configuration."""

import importlib
from pathlib import Path

import pytest
from pydantic import HttpUrl

from unique_mcp import settings as settings_module
from unique_mcp.settings import ServerSettings


@pytest.mark.ai
def test_server_settings__uses_default_values__when_no_env_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify ServerSettings uses default values when env vars are not set.
    Why this matters: Ensures the settings have sensible defaults for development.
    Setup summary: Clear env vars, verify defaults are used.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_MCP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    # Act
    settings = ServerSettings()

    # Assert
    assert settings.public_base_url is None
    assert settings.local_base_url == HttpUrl("http://localhost:8003")


@pytest.mark.ai
def test_server_settings__loads_public_base_url__from_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify ServerSettings loads public_base_url from environment variable.
    Why this matters: Ensures configuration can be set via environment variables.
    Setup summary: Set UNIQUE_MCP_PUBLIC_BASE_URL env var, verify it's loaded.
    """
    # Arrange
    test_url = "https://example.com"
    monkeypatch.setenv("UNIQUE_MCP_PUBLIC_BASE_URL", test_url)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    # Act
    settings = ServerSettings()

    # Assert
    assert settings.public_base_url == HttpUrl(test_url)


@pytest.mark.ai
def test_server_settings__loads_local_base_url__from_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify ServerSettings loads local_base_url from environment variable.
    Why this matters: Ensures local configuration can be customized via environment.
    Setup summary: Set UNIQUE_MCP_LOCAL_BASE_URL env var, verify it's loaded.
    """
    # Arrange
    test_url = "http://localhost:9000"
    monkeypatch.setenv("UNIQUE_MCP_LOCAL_BASE_URL", test_url)
    monkeypatch.delenv("UNIQUE_MCP_PUBLIC_BASE_URL", raising=False)

    # Act
    settings = ServerSettings()

    # Assert
    assert settings.local_base_url == HttpUrl(test_url)


@pytest.mark.ai
def test_server_settings__loads_from_env_file__when_file_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify ServerSettings loads configuration from env file when it exists.
    Why this matters: Ensures file-based configuration works correctly.
    Setup summary: Create env file, set ENVIRONMENT_FILE_PATH, reload, verify values.
    """
    # Arrange
    env_file = tmp_path / "unique_mcp.env"
    env_file.write_text(
        "UNIQUE_MCP_PUBLIC_BASE_URL=https://prod.example.com\n"
        "UNIQUE_MCP_LOCAL_BASE_URL=http://localhost:9000\n"
    )
    monkeypatch.setenv("ENVIRONMENT_FILE_PATH", str(env_file))
    monkeypatch.delenv("UNIQUE_MCP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    # Act
    importlib.reload(settings_module)
    server_settings = settings_module.ServerSettings()

    # Assert
    assert server_settings.public_base_url == HttpUrl("https://prod.example.com")
    assert server_settings.local_base_url == HttpUrl("http://localhost:9000")


@pytest.mark.ai
def test_server_settings__base_url__returns_public_base_url__when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify base_url property returns public_base_url when it is set.
    Why this matters: Ensures public URL takes precedence over local URL.
    Setup summary: Create settings with public_base_url set, verify base_url returns it.
    """
    # Arrange
    public_url = HttpUrl("https://example.com")
    monkeypatch.delenv("UNIQUE_MCP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    # Act
    settings = ServerSettings(public_base_url=public_url)

    # Assert
    assert settings.base_url == public_url


@pytest.mark.ai
def test_server_settings__base_url__returns_local_base_url__when_public_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify base_url property returns local_base_url when public not set.
    Why this matters: Ensures fallback to local URL works correctly.
    Setup summary: Create settings without public_base_url, verify local returned.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_MCP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    # Act
    settings = ServerSettings()

    # Assert
    assert settings.base_url == settings.local_base_url
    assert settings.base_url == HttpUrl("http://localhost:8003")


@pytest.mark.ai
@pytest.mark.parametrize(
    "scheme,expected_transport",
    [
        ("http", "http"),
        ("https", "http"),
    ],
    ids=["http", "https"],
)
def test_server_settings__transport_scheme__returns_correct_transport__for_valid_schemes(  # noqa: E501
    scheme: str, expected_transport: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Purpose: Verify transport_scheme returns correct Transport for valid URL schemes.
    Why this matters: Ensures correct transport type is determined from URL scheme.
    Setup summary: Set URL with http/https schemes, verify correct transport returned.
    """
    # Arrange
    test_url = f"{scheme}://example.com"
    monkeypatch.setenv("UNIQUE_MCP_PUBLIC_BASE_URL", test_url)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    # Act
    settings = ServerSettings()

    # Assert
    assert settings.transport_scheme == expected_transport


@pytest.mark.ai
def test_server_settings__transport_scheme__uses_local_base_url__when_public_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify transport_scheme uses local_base_url when public_base_url not set.
    Why this matters: Ensures transport scheme is determined from local URL as fallback.
    Setup summary: Create settings without public_base_url, verify local URL used.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_MCP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    # Act
    settings = ServerSettings()

    # Assert
    assert settings.transport_scheme == "http"


@pytest.mark.ai
def test_server_settings__validates_url_scheme__rejects_non_http_schemes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify ServerSettings validates URL scheme, rejects non-http/https.
    Why this matters: Ensures invalid URL schemes are caught during config loading.
    Setup summary: Set URL with invalid scheme (ftp), verify ValidationError raised.
    """
    # Arrange
    invalid_url = "ftp://example.com"
    monkeypatch.setenv("UNIQUE_MCP_PUBLIC_BASE_URL", invalid_url)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    # Act & Assert
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        ServerSettings()

    error_str = str(exc_info.value)
    assert "url_scheme" in error_str or "scheme" in error_str.lower()


@pytest.mark.ai
def test_server_settings__is_frozen__prevents_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify ServerSettings is frozen and prevents field mutation.
    Why this matters: Ensures configuration immutability for safety.
    Setup summary: Create settings instance, attempt to modify field, verify error.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_MCP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    settings = ServerSettings()

    # Act & Assert
    with pytest.raises(Exception):  # Pydantic ValidationError for frozen models
        settings.local_base_url = HttpUrl("http://localhost:9999")  # type: ignore[misc]


@pytest.mark.ai
def test_server_settings__handles_none_env_file__gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify ServerSettings handles None return from find_env_file gracefully.
    Why this matters: Ensures settings work when no env file is found (required=False).
    Setup summary: Ensure no env file exists, verify settings work with defaults.
    """
    # Arrange
    monkeypatch.delenv("ENVIRONMENT_FILE_PATH", raising=False)
    monkeypatch.delenv("UNIQUE_MCP_PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    # Act
    settings = ServerSettings()

    # Assert
    assert settings.public_base_url is None
    assert settings.local_base_url == HttpUrl("http://localhost:8003")
    assert settings.base_url == HttpUrl("http://localhost:8003")


@pytest.mark.ai
def test_server_settings__validates_url_format__from_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify ServerSettings validates URL format from environment variables.
    Why this matters: Ensures invalid URLs are caught during configuration loading.
    Setup summary: Set invalid URL in env var, verify validation error is raised.
    """
    # Arrange
    invalid_url = "not-a-valid-url"
    monkeypatch.setenv("UNIQUE_MCP_PUBLIC_BASE_URL", invalid_url)
    monkeypatch.delenv("UNIQUE_MCP_LOCAL_BASE_URL", raising=False)

    # Act & Assert
    with pytest.raises(Exception):  # Pydantic ValidationError
        ServerSettings()
