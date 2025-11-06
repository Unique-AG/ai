"""
Unit tests for config.py module.
"""

import pytest

from unique_deep_research.config import TEMPLATE_DIR, TEMPLATE_ENV


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
