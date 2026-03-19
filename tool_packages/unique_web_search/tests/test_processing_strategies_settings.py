"""Tests for processing_strategies settings module — get_settings() branches."""

from unittest.mock import patch

import pytest

from unique_web_search.services.content_processing.processing_strategies.settings import (
    ProcessingStrategiesSettings,
    Settings,
    TestSettings,
    get_settings,
)


class TestGetSettings:
    @pytest.mark.ai
    def test_get_settings__under_pytest__returns_test_settings(self) -> None:
        result = get_settings()
        assert isinstance(result, TestSettings)

    @pytest.mark.ai
    def test_get_settings__not_under_pytest__returns_production_settings(
        self,
    ) -> None:
        import sys

        sys.modules.copy()
        modules_without_pytest = {k: v for k, v in sys.modules.items() if k != "pytest"}
        with patch.dict("sys.modules", modules_without_pytest, clear=True):
            result = get_settings()
        assert isinstance(result, Settings)

    @pytest.mark.ai
    def test_settings__is_processing_strategies_settings(self) -> None:
        result = get_settings()
        assert isinstance(result, ProcessingStrategiesSettings)
