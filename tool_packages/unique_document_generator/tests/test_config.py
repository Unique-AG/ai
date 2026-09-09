"""Unit tests for the DocGenerator config module."""

import pytest

from unique_document_generator.config import (
    DEFAULT_TOOL_DESCRIPTION,
    DocGeneratorToolConfig,
    ExportFormat,
)


class TestDocGeneratorToolConfig:
    @pytest.mark.ai
    def test_doc_generator_tool_config__uses_expected_defaults__when_initialized_without_overrides(
        self,
    ) -> None:
        """
        Purpose: Verify the config defaults match the intended out-of-the-box tool behavior.
        Why this matters: New tool instances depend on these defaults for prompt text, format, and template handling.
        Setup summary: Create a default config and assert each supported field uses the expected default value.
        """
        # Arrange
        config = DocGeneratorToolConfig()

        # Act / Assert
        assert config.template_content_id == ""
        assert config.export_format == ExportFormat.DOCX
        assert config.tool_description == DEFAULT_TOOL_DESCRIPTION
        assert config.tool_format_information_for_system_prompt == ""
        assert not hasattr(config, "tool_description_for_system_prompt")
        assert not hasattr(config, "tool_description_for_user_prompt")
        assert not hasattr(config, "tool_format_information_for_user_prompt")
        assert not hasattr(config, "tool_format_reminder_for_user_prompt")

    @pytest.mark.ai
    def test_doc_generator_tool_config__stores_template_content_id__when_provided(
        self,
    ) -> None:
        """
        Purpose: Verify the config preserves a configured template content id.
        Why this matters: Template-driven branding depends on passing the configured knowledge-base content id through unchanged.
        Setup summary: Build the config with a template id and assert the stored value matches.
        """
        # Arrange
        config = DocGeneratorToolConfig(template_content_id="cont_abc123")

        # Act
        result = config.template_content_id

        # Assert
        assert result == "cont_abc123"

    @pytest.mark.ai
    def test_doc_generator_tool_config__stores_tool_description__when_overridden(
        self,
    ) -> None:
        """
        Purpose: Verify the config preserves a custom tool description.
        Why this matters: Prompt tuning in the UI should reach the runtime configuration exactly as entered.
        Setup summary: Build the config with a custom description and assert it is stored verbatim.
        """
        # Arrange
        config = DocGeneratorToolConfig(tool_description="Custom description")

        # Act
        result = config.tool_description

        # Assert
        assert result == "Custom description"

    @pytest.mark.ai
    def test_doc_generator_tool_config__round_trips_serialization__when_dumped_and_restored(
        self,
    ) -> None:
        """
        Purpose: Verify the config survives model serialization and validation round-trips.
        Why this matters: Tool settings are persisted and reloaded through serialized config payloads.
        Setup summary: Dump a populated config to a dict, restore it, and assert key fields are preserved.
        """
        # Arrange
        config = DocGeneratorToolConfig(
            template_content_id="cont_xyz",
            export_format=ExportFormat.DOCX,
        )

        # Act
        data = config.model_dump()
        restored = DocGeneratorToolConfig.model_validate(data)

        # Assert
        assert restored.template_content_id == "cont_xyz"
        assert restored.export_format == ExportFormat.DOCX


class TestExportFormat:
    @pytest.mark.ai
    def test_export_format__docx__uses_expected_string_value(self) -> None:
        """
        Purpose: Verify the DOCX enum value maps to the expected serialized string.
        Why this matters: The config schema and UI depend on stable enum values for persistence.
        Setup summary: Read the enum member and assert both the member comparison and raw value match `docx`.
        """
        # Arrange / Act / Assert
        assert ExportFormat.DOCX == "docx"
        assert ExportFormat.DOCX.value == "docx"
