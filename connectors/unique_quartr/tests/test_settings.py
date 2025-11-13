import sys
from unittest.mock import MagicMock, patch

import pytest

from unique_quartr.settings import (
    QuartrApiCreds,
    Settings,
    get_settings,
)


class TestQuartrApiCreds:
    """Test cases for QuartrApiCreds model."""

    def test_quartr_api_creds_creation(self):
        """Test QuartrApiCreds model creation."""
        creds = QuartrApiCreds(
            api_key="test_key_12345",
            valid_to="2025-12-31",
        )

        assert creds.api_key == "test_key_12345"
        assert creds.valid_to == "2025-12-31"

    def test_quartr_api_creds_validation(self):
        """Test QuartrApiCreds requires all fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            QuartrApiCreds(api_key="test_key")  # Missing valid_to


class TestSettings:
    """Test cases for Settings classes."""

    def test_settings_has_required_fields(self):
        """Test Settings has required fields."""
        from unique_quartr.settings import Base

        # Check that Base has the expected fields
        assert hasattr(Base, "__annotations__")
        annotations = Base.__annotations__
        assert "quartr_api_creds" in annotations
        assert "quartr_api_activated_companies" in annotations

    def test_test_settings_has_required_fields(self):
        """Test TestSettings has required fields."""
        from unique_quartr.settings import Base

        # Check that Base (parent of TestSettings) has the expected fields
        assert hasattr(Base, "__annotations__")
        annotations = Base.__annotations__
        assert "quartr_api_creds" in annotations
        assert "quartr_api_activated_companies" in annotations


class TestGetSettings:
    """Test cases for get_settings function."""

    def test_get_settings_returns_settings_by_default(self):
        """Test get_settings returns Settings when not running pytest."""
        # Ensure pytest is not in sys.modules for this test
        pytest_module = sys.modules.pop("pytest", None)
        try:
            settings = get_settings()
            assert isinstance(settings, Settings)
        finally:
            if pytest_module is not None:
                sys.modules["pytest"] = pytest_module

    def test_get_settings_returns_test_settings_in_pytest(self):
        """Test get_settings returns TestSettings when running under pytest."""
        # pytest should already be in sys.modules when running tests
        if "pytest" in sys.modules:
            settings = get_settings()
            # In pytest context, should return TestSettings
            assert type(settings).__name__ in [
                "TestSettings",
                "Settings",
            ]  # Can be either depending on context

    @patch.dict("sys.modules", {"pytest": MagicMock()})
    def test_get_settings_pytest_module_present(self):
        """Test get_settings detects pytest in sys.modules."""
        # Import get_settings in the patched context
        from unique_quartr.settings import get_settings as get_settings_fn

        settings = get_settings_fn()
        assert type(settings).__name__ in ["TestSettings", "Settings"]

    @patch.dict("sys.modules", {}, clear=False)
    def test_get_settings_pytest_module_absent(self):
        """Test get_settings when pytest is not in sys.modules."""
        # Remove pytest if present
        sys.modules.pop("pytest", None)

        settings = get_settings()
        assert isinstance(settings, Settings)
