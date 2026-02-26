"""
Unit tests for config.py module.
"""

import pytest

from unique_deep_research.config import TEMPLATE_DIR, TEMPLATE_ENV, WebToolsConfig


@pytest.mark.ai
def test_template_dir__exists__and_is_directory() -> None:
    """
    Purpose: Verify TEMPLATE_DIR points to existing templates directory.
    Why this matters: Template directory is required for Jinja2 template loading.
    Setup summary: Check TEMPLATE_DIR exists and is a directory.
    """
    # Assert
    assert TEMPLATE_DIR.exists()
    assert TEMPLATE_DIR.is_dir()


@pytest.mark.ai
def test_template_env__is_configured__with_correct_loader() -> None:
    """
    Purpose: Verify TEMPLATE_ENV is properly configured with FileSystemLoader.
    Why this matters: Template environment is used throughout the application for rendering.
    Setup summary: Check template environment loader configuration.
    """
    # Assert
    assert TEMPLATE_ENV is not None
    assert hasattr(TEMPLATE_ENV, "loader")
    assert str(TEMPLATE_DIR) in str(TEMPLATE_ENV.loader.searchpath)


@pytest.mark.ai
def test_web_tools_config__show_full_page_result__defaults_to_false() -> None:
    """
    Purpose: Verify show_full_page_result defaults to False in WebToolsConfig.
    Why this matters: Full page content should only be included when explicitly enabled.
    Setup summary: Instantiate default WebToolsConfig, assert show_full_page_result is False.
    """
    # Arrange & Act
    config = WebToolsConfig()

    # Assert
    assert config.show_full_page_result is False


@pytest.mark.ai
def test_web_tools_config__show_full_page_result__can_be_enabled() -> None:
    """
    Purpose: Verify show_full_page_result can be set to True.
    Why this matters: Users need to be able to enable full page content in search results.
    Setup summary: Instantiate WebToolsConfig with show_full_page_result=True, assert value.
    """
    # Arrange & Act
    config = WebToolsConfig(show_full_page_result=True)

    # Assert
    assert config.show_full_page_result is True
