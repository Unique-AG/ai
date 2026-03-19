"""Tests for ContentProcessorConfig.active_processing_strategies property."""

import pytest

from unique_web_search.services.content_processing.cleaning.config import (
    CleaningConfig,
    LineRemovalPatternsConfig,
)
from unique_web_search.services.content_processing.config import (
    ContentProcessorConfig,
)


class TestActiveProcessingStrategies:
    @pytest.mark.ai
    def test_active_strategies__all_enabled__returns_all_names(self) -> None:
        config = ContentProcessorConfig(
            cleaning=CleaningConfig(
                enable_character_sanitize=True,
                line_removal=LineRemovalPatternsConfig(enabled=True),
                enable_markdown_cleaning=True,
            ),
        )
        config.processing_strategies.truncate.enabled = True
        config.processing_strategies.llm_processor.enabled = True
        strategies = config.active_processing_strategies
        assert "character_sanitize" in strategies
        assert "line_removal" in strategies
        assert "markdown_transformation" in strategies
        assert "truncate" in strategies
        assert "llm_processor" in strategies

    @pytest.mark.ai
    def test_active_strategies__all_disabled__returns_empty(self) -> None:
        config = ContentProcessorConfig(
            cleaning=CleaningConfig(
                enable_character_sanitize=False,
                line_removal=LineRemovalPatternsConfig(enabled=False),
                enable_markdown_cleaning=False,
            ),
        )
        config.processing_strategies.truncate.enabled = False
        config.processing_strategies.llm_processor.enabled = False
        strategies = config.active_processing_strategies
        assert strategies == []

    @pytest.mark.ai
    def test_active_strategies__character_sanitize_enabled__appears_in_list(
        self,
    ) -> None:
        config = ContentProcessorConfig(
            cleaning=CleaningConfig(
                enable_character_sanitize=True,
                line_removal=LineRemovalPatternsConfig(enabled=False),
                enable_markdown_cleaning=False,
            ),
        )
        config.processing_strategies.truncate.enabled = False
        config.processing_strategies.llm_processor.enabled = False
        assert config.active_processing_strategies == ["character_sanitize"]

    @pytest.mark.ai
    def test_active_strategies__only_line_removal_enabled__appears_in_list(
        self,
    ) -> None:
        config = ContentProcessorConfig(
            cleaning=CleaningConfig(
                enable_character_sanitize=False,
                line_removal=LineRemovalPatternsConfig(enabled=True),
                enable_markdown_cleaning=False,
            ),
        )
        config.processing_strategies.truncate.enabled = False
        config.processing_strategies.llm_processor.enabled = False
        assert config.active_processing_strategies == ["line_removal"]

    @pytest.mark.ai
    def test_active_strategies__default_config__returns_default_enabled(self) -> None:
        config = ContentProcessorConfig()
        strategies = config.active_processing_strategies
        assert "character_sanitize" in strategies
        assert "line_removal" in strategies
        assert "markdown_transformation" in strategies
        assert "truncate" in strategies
