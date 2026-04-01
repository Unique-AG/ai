from pathlib import Path

import pytest

from unique_toolkit.app import EnvFileNotFoundError, find_env_file


@pytest.mark.ai
def test_AI_find_env_file__returns_path__from_env_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Purpose: Verify find_env_file prioritizes ENVIRONMENT_FILE_PATH environment variable.
    Why this matters: Ensures explicit configuration takes precedence over CWD and config dir.
    Setup summary: Set ENVIRONMENT_FILE_PATH, create file at that path, assert it's found.
    """
    # Arrange
    env_file = tmp_path / "custom.env"
    env_file.write_text("TEST=value")
    monkeypatch.setenv("ENVIRONMENT_FILE_PATH", str(env_file))
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
    Why this matters: Ensures standard location discovery works when no env variable is set.
    Setup summary: Clear ENVIRONMENT_FILE_PATH, create .env in cwd, assert it's found.
    """
    # Arrange
    monkeypatch.delenv("ENVIRONMENT_FILE_PATH", raising=False)
    env_file = tmp_path / ".env"
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
    Setup summary: Clear ENVIRONMENT_FILE_PATH, ensure no file exists, assert exception with helpful message.
    """
    # Arrange
    monkeypatch.delenv("ENVIRONMENT_FILE_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    # Act & Assert
    with pytest.raises(EnvFileNotFoundError) as exc_info:
        find_env_file()
    assert "not found" in str(exc_info.value)
    assert ".env" in str(exc_info.value)
