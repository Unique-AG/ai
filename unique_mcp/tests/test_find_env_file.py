"""Tests for find_env_file utility function."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from unique_mcp.util.find_env_file import EnvFileNotFoundError, find_env_file


@pytest.mark.ai
def test_find_env_file__finds_file__in_current_directory(tmp_path: Path) -> None:
    """
    Purpose: Verify find_env_file finds a file in the current working directory.
    Why this matters: Ensures the function correctly searches the CWD.
    Setup summary: Create a test file in temp directory, change to it, verify file is found.
    """
    # Arrange
    test_file = tmp_path / ".env"
    test_file.write_text("TEST=value")
    original_cwd = os.getcwd()

    try:
        os.chdir(tmp_path)
        # Act
        result = find_env_file(filenames=[".env"])

        # Assert
        assert result == test_file
        assert result is not None
        assert result.exists()
    finally:
        os.chdir(original_cwd)


@pytest.mark.ai
def test_find_env_file__finds_file__via_environment_variable(tmp_path: Path) -> None:
    """
    Purpose: Verify find_env_file finds a file specified by ENVIRONMENT_FILE_PATH.
    Why this matters: Ensures the function respects explicit environment variable.
    Setup summary: Create a test file, set ENVIRONMENT_FILE_PATH, verify file is found.
    """
    # Arrange
    test_file = tmp_path / "custom.env"
    test_file.write_text("TEST=value")

    # Act
    with patch.dict(os.environ, {"ENVIRONMENT_FILE_PATH": str(test_file)}):
        result = find_env_file(filenames=["custom.env"])

    # Assert
    assert result is not None
    assert result == test_file
    assert result.exists()


@pytest.mark.ai
def test_find_env_file__finds_file__in_user_config_directory(
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify find_env_file finds a file in the user config directory.
    Why this matters: Ensures the function correctly searches platform-specific config dirs.
    Setup summary: Mock user_config_dir, create file there, verify file is found.
    """
    # Arrange
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    test_file = config_dir / ".env"
    test_file.write_text("TEST=value")

    # Act
    with patch(
        "unique_mcp.util.find_env_file.user_config_dir",
        return_value=str(config_dir),
    ):
        result = find_env_file(filenames=[".env"])

    # Assert
    assert result == test_file
    assert result is not None
    assert result.exists()


@pytest.mark.ai
def test_find_env_file__raises_error__when_file_not_found_and_required() -> None:
    """
    Purpose: Verify find_env_file raises EnvFileNotFoundError when file is not found and required=True.
    Why this matters: Ensures proper error handling when file is missing.
    Setup summary: Search for non-existent file with required=True, verify error is raised.
    """
    # Arrange & Act & Assert
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(EnvFileNotFoundError) as exc_info:
            find_env_file(filenames=["nonexistent.env"], required=True)

        error_message = str(exc_info.value)
        assert "nonexistent.env" in error_message
        assert "not found" in error_message


@pytest.mark.ai
def test_find_env_file__returns_none__when_file_not_found_and_not_required() -> None:
    """
    Purpose: Verify find_env_file returns None when file is not found and required=False.
    Why this matters: Ensures optional file lookup works correctly, allowing env vars to be used directly.
    Setup summary: Search for non-existent file with required=False, verify None is returned.
    """
    # Arrange & Act
    with patch.dict(os.environ, {}, clear=True):
        result = find_env_file(filenames=["nonexistent.env"], required=False)

    # Assert
    assert result is None


@pytest.mark.ai
def test_find_env_file__prioritizes_environment_variable__over_other_locations(
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify find_env_file prioritizes ENVIRONMENT_FILE_PATH over CWD and config dir.
    Why this matters: Ensures explicit configuration takes precedence.
    Setup summary: Create files in multiple locations, set ENVIRONMENT_FILE_PATH, verify correct file is found.
    """
    # Arrange
    env_file = tmp_path / "env.env"
    env_file.write_text("ENV_VAR=env")

    cwd_file = tmp_path / "cwd.env"
    cwd_file.write_text("ENV_VAR=cwd")
    original_cwd = os.getcwd()

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "cwd.env"
    config_file.write_text("ENV_VAR=config")

    try:
        os.chdir(tmp_path)
        # Act
        with patch.dict(os.environ, {"ENVIRONMENT_FILE_PATH": str(env_file)}):
            with patch(
                "unique_mcp.util.find_env_file.user_config_dir",
                return_value=str(config_dir),
            ):
                result = find_env_file(filenames=["cwd.env"])

        # Assert
        assert result == env_file
        assert result is not None
        assert result.read_text() == "ENV_VAR=env"
    finally:
        os.chdir(original_cwd)


@pytest.mark.ai
def test_find_env_file__prioritizes_cwd__over_config_directory(
    tmp_path: Path,
) -> None:
    """
    Purpose: Verify find_env_file prioritizes CWD over config directory when ENVIRONMENT_FILE_PATH is not set.
    Why this matters: Ensures correct search order fallback.
    Setup summary: Create files in CWD and config dir, verify CWD file is found.
    """
    # Arrange
    cwd_file = tmp_path / "test.env"
    cwd_file.write_text("ENV_VAR=cwd")
    original_cwd = os.getcwd()

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "test.env"
    config_file.write_text("ENV_VAR=config")

    try:
        os.chdir(tmp_path)
        # Act
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "unique_mcp.util.find_env_file.user_config_dir",
                return_value=str(config_dir),
            ):
                result = find_env_file(filenames=["test.env"])

        # Assert
        assert result == cwd_file
        assert result is not None
        assert result.read_text() == "ENV_VAR=cwd"
    finally:
        os.chdir(original_cwd)


@pytest.mark.ai
def test_find_env_file__uses_custom_filename() -> None:
    """
    Purpose: Verify find_env_file works with custom filenames.
    Why this matters: Ensures the function is flexible for different env file names.
    Setup summary: Create file with custom name, verify it's found.
    """
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "zitadel.env"
        test_file.write_text("TEST=value")
        original_cwd = os.getcwd()

        try:
            os.chdir(tmpdir)
            # Act
            result = find_env_file(filenames=["zitadel.env"])

            # Assert
            assert result is not None
            assert result.resolve() == test_file.resolve()
            assert result.exists()
        finally:
            os.chdir(original_cwd)


@pytest.mark.ai
def test_find_env_file__uses_custom_app_name_and_author(tmp_path: Path) -> None:
    """
    Purpose: Verify find_env_file uses custom app_name and app_author for config directory.
    Why this matters: Ensures the function respects custom application identifiers.
    Setup summary: Mock user_config_dir with custom app name/author, verify correct path is used.
    """
    # Arrange
    config_dir = tmp_path / "custom_app" / "config"
    config_dir.mkdir(parents=True)
    test_file = config_dir / ".env"
    test_file.write_text("TEST=value")

    # Act
    with patch(
        "unique_mcp.util.find_env_file.user_config_dir",
        return_value=str(config_dir),
    ):
        result = find_env_file(
            filenames=[".env"], app_name="custom_app", app_author="custom_author"
        )

    # Assert
    assert result == test_file
    assert result is not None
    assert result.exists()


@pytest.mark.ai
def test_find_env_file__ignores_directories(tmp_path: Path) -> None:
    """
    Purpose: Verify find_env_file ignores directories with the same name as the env file.
    Why this matters: Ensures only files are matched, not directories.
    Setup summary: Create a directory with env file name, verify it's ignored.
    """
    # Arrange
    env_dir = tmp_path / ".env"
    env_dir.mkdir()
    env_file = tmp_path / "actual.env"
    env_file.write_text("TEST=value")
    original_cwd = os.getcwd()

    try:
        os.chdir(tmp_path)
        # Act
        result = find_env_file(filenames=["actual.env"])

        # Assert
        assert result == env_file
        assert result is not None
        assert result.is_file()
    finally:
        os.chdir(original_cwd)
