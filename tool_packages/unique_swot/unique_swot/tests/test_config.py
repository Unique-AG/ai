"""Tests for SWOT configuration module."""

from unique_swot.config import TOOL_DESCRIPTION, SwotConfig
from unique_swot.services.generation import ReportGenerationConfig


class TestSwotConfig:
    """Test cases for SwotConfig class."""

    def test_swot_config_default_values(self):
        """Test that SwotConfig initializes with correct default values."""
        config = SwotConfig()

        assert config.cache_scope_id == "swot_analysis"
        assert isinstance(config.report_generation_config, ReportGenerationConfig)
        assert config.tool_description == TOOL_DESCRIPTION
        assert config.tool_description_for_system_prompt == TOOL_DESCRIPTION
        assert config.tool_format_information_for_system_prompt == TOOL_DESCRIPTION
        assert (
            config.tool_description_for_user_prompt
            == "The user prompt for the SWOT analysis tool."
        )
        assert config.tool_format_information_for_user_prompt == TOOL_DESCRIPTION
        assert (
            config.tool_format_reminder_for_user_prompt
            == "The format reminder for the SWOT analysis tool."
        )

    def test_swot_config_custom_cache_scope_id(self):
        """Test SwotConfig with custom cache_scope_id."""
        custom_scope = "custom_swot_scope"
        config = SwotConfig(cache_scope_id=custom_scope)

        assert config.cache_scope_id == custom_scope

    def test_swot_config_custom_report_generation_config(self):
        """Test SwotConfig with custom report generation config."""
        custom_report_config = ReportGenerationConfig(
            batch_size=5,
            max_tokens_per_batch=2000,
        )
        config = SwotConfig(report_generation_config=custom_report_config)

        assert config.report_generation_config.batch_size == 5
        assert config.report_generation_config.max_tokens_per_batch == 2000

    def test_swot_config_custom_descriptions(self):
        """Test SwotConfig with custom description fields."""
        custom_desc = "Custom description"
        config = SwotConfig(
            tool_description=custom_desc,
            tool_description_for_system_prompt=custom_desc,
            tool_format_information_for_system_prompt=custom_desc,
        )

        assert config.tool_description == custom_desc
        assert config.tool_description_for_system_prompt == custom_desc
        assert config.tool_format_information_for_system_prompt == custom_desc

    def test_tool_description_contains_key_information(self):
        """Test that TOOL_DESCRIPTION contains expected key information."""
        assert "SWOT" in TOOL_DESCRIPTION
        assert "analysis" in TOOL_DESCRIPTION.lower()
        assert (
            "strengths" in TOOL_DESCRIPTION.lower()
            or "weaknesses" in TOOL_DESCRIPTION.lower()
        )

    def test_swot_config_serialization(self):
        """Test that SwotConfig can be serialized and deserialized."""
        config = SwotConfig(cache_scope_id="test_scope")
        config_dict = config.model_dump()

        assert config_dict["cache_scope_id"] == "test_scope"

        # Recreate from dict
        config_restored = SwotConfig.model_validate(config_dict)
        assert config_restored.cache_scope_id == "test_scope"
