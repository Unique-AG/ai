from pathlib import Path

import pytest

from unique_toolkit.app import EnvFileNotFoundError, find_env_file


@pytest.mark.ai
def test_AI_find_env_file__returns_path__from_env_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Purpose: Verify find_env_file prioritizes UNIQUE_ENV_FILE environment variable.
    Why this matters: Ensures explicit configuration takes precedence.
    Setup summary: Set UNIQUE_ENV_FILE, create file at that path, assert it's found.
    """
    # Arrange
    env_file = tmp_path / "custom.env"
    env_file.write_text("TEST=value")
    monkeypatch.setenv("UNIQUE_ENV_FILE", str(env_file))
    # Act
    found_path = find_env_file()
    # Assert
    assert found_path == env_file


@pytest.mark.ai
def test_AI_find_env_file__returns_path__from_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Purpose: Verify find_env_file falls back to current working directory.
    Why this matters: Ensures standard location discovery works.
    Setup summary: Remove UNIQUE_ENV_FILE, create file in cwd, assert it's found.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_ENV_FILE", raising=False)
    env_file = tmp_path / "unique.env"
    env_file.write_text("TEST=value")
    monkeypatch.chdir(tmp_path)
    # Act
    found_path = find_env_file()
    # Assert
    assert found_path == env_file


@pytest.mark.ai
def test_AI_find_env_file__raises_error__when_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Purpose: Verify find_env_file raises EnvFileNotFoundError when file doesn't exist.
    Why this matters: Provides clear error message when configuration is missing.
    Setup summary: Remove UNIQUE_ENV_FILE, ensure no file exists, assert exception with helpful message.
    """
    # Arrange
    monkeypatch.delenv("UNIQUE_ENV_FILE", raising=False)
    monkeypatch.chdir(tmp_path)
    # Act & Assert
    with pytest.raises(EnvFileNotFoundError) as exc_info:
        find_env_file()
    assert "not found" in str(exc_info.value)
    assert "UNIQUE_ENV_FILE" in str(exc_info.value)
