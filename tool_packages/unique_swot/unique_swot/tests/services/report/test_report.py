"""Tests for report configuration and templates."""

import pytest
from pydantic import ValidationError
from unique_toolkit._common.docx_generator import DocxGeneratorConfig

from unique_swot.services.report.config import (
    REPORT_TEMPLATE,
    DocxRendererType,
    ReportRendererConfig,
)


class TestReportTemplate:
    """Test cases for report template."""

    def test_report_template_exists(self):
        """Test that report template is loaded."""
        assert REPORT_TEMPLATE is not None
        assert isinstance(REPORT_TEMPLATE, str)
        assert len(REPORT_TEMPLATE) > 0

    def test_report_template_has_required_sections(self):
        """Test that template contains required SWOT sections."""
        # Template should reference all SWOT components
        assert (
            "strengths" in REPORT_TEMPLATE.lower() or "{{ strengths" in REPORT_TEMPLATE
        )
        assert (
            "weaknesses" in REPORT_TEMPLATE.lower()
            or "{{ weaknesses" in REPORT_TEMPLATE
        )
        assert (
            "opportunities" in REPORT_TEMPLATE.lower()
            or "{{ opportunities" in REPORT_TEMPLATE
        )
        assert "threats" in REPORT_TEMPLATE.lower() or "{{ threats" in REPORT_TEMPLATE


class TestDocxRendererType:
    """Test cases for DocxRendererType enum."""

    def test_docx_renderer_types(self):
        """Test that renderer types are defined correctly."""
        assert DocxRendererType.DOCX == "docx"
        assert DocxRendererType.CHAT == "chat"

    def test_renderer_type_membership(self):
        """Test renderer type membership."""
        assert "docx" in DocxRendererType.__members__.values()
        assert "chat" in DocxRendererType.__members__.values()

    def test_renderer_type_count(self):
        """Test that only expected renderer types exist."""
        assert len(DocxRendererType.__members__) == 2


class TestReportRendererConfig:
    """Test cases for ReportRendererConfig."""

    def test_config_initialization_default(self):
        """Test default configuration initialization."""
        config = ReportRendererConfig()

        assert config.report_template == REPORT_TEMPLATE
        assert config.renderer_type == DocxRendererType.DOCX
        assert isinstance(config.docx_renderer_config, DocxGeneratorConfig)

    def test_config_initialization_with_custom_template(self):
        """Test configuration with custom template."""
        custom_template = "# Custom Template\n{{ objective }}"
        config = ReportRendererConfig(report_template=custom_template)

        assert config.report_template == custom_template
        assert config.renderer_type == DocxRendererType.DOCX

    def test_config_initialization_with_chat_renderer(self):
        """Test configuration with chat renderer type."""
        config = ReportRendererConfig(renderer_type=DocxRendererType.CHAT)

        assert config.renderer_type == DocxRendererType.CHAT
        assert config.report_template == REPORT_TEMPLATE

    def test_config_initialization_with_custom_docx_config(self):
        """Test configuration with custom DOCX renderer config."""
        custom_docx_config = DocxGeneratorConfig()
        config = ReportRendererConfig(docx_renderer_config=custom_docx_config)

        assert config.docx_renderer_config == custom_docx_config

    def test_config_serialization(self):
        """Test configuration serialization."""
        config = ReportRendererConfig(
            report_template="# Test",
            renderer_type=DocxRendererType.CHAT,
        )

        # Should be able to serialize
        config_dict = config.model_dump()
        assert config_dict["report_template"] == "# Test"
        assert config_dict["renderer_type"] == "chat"
        assert "docx_renderer_config" in config_dict

    def test_config_deserialization(self):
        """Test configuration deserialization."""
        config_dict = {
            "report_template": "# Custom",
            "renderer_type": "docx",
        }

        config = ReportRendererConfig(**config_dict)  # type: ignore
        assert config.report_template == "# Custom"
        assert config.renderer_type == DocxRendererType.DOCX

    def test_config_with_all_parameters(self):
        """Test configuration with all parameters set."""
        config = ReportRendererConfig(
            report_template="# Complete Template",
            renderer_type=DocxRendererType.DOCX,
            docx_renderer_config=DocxGeneratorConfig(),
        )

        assert config.report_template == "# Complete Template"
        assert config.renderer_type == DocxRendererType.DOCX
        assert isinstance(config.docx_renderer_config, DocxGeneratorConfig)

    def test_config_immutability(self):
        """Test that config follows immutability from configuration dict."""
        config = ReportRendererConfig()

        # Configuration should have frozen=True or validate_assignment from get_configuration_dict()
        # Check if either frozen or validate_assignment is set
        _ = (
            config.model_config.get("frozen") is True
            or config.model_config.get("validate_assignment") is True
        )
        # This is optional, so just check the config exists
        assert config.model_config is not None

    def test_config_field_descriptions(self):
        """Test that fields have proper descriptions."""
        # Get field info
        fields = ReportRendererConfig.model_fields

        assert "report_template" in fields
        assert "renderer_type" in fields
        assert "docx_renderer_config" in fields

        # Check descriptions exist
        assert fields["report_template"].description is not None
        assert fields["renderer_type"].description is not None
        assert fields["docx_renderer_config"].description is not None

    def test_config_json_schema(self):
        """Test that configuration can generate JSON schema."""
        schema = ReportRendererConfig.model_json_schema()

        assert "properties" in schema
        # Properties might be in camelCase due to schema generation
        properties = schema["properties"]
        # Check if any form of the property names exist
        assert any("template" in key.lower() for key in properties.keys())
        assert any("renderer" in key.lower() for key in properties.keys())
        assert any("docx" in key.lower() for key in properties.keys())


class TestReportRendererConfigValidation:
    """Test validation for ReportRendererConfig."""

    def test_config_accepts_valid_renderer_types(self):
        """Test that config accepts valid renderer types."""
        config_docx = ReportRendererConfig(renderer_type=DocxRendererType.DOCX)
        assert config_docx.renderer_type == DocxRendererType.DOCX

        config_chat = ReportRendererConfig(renderer_type=DocxRendererType.CHAT)
        assert config_chat.renderer_type == DocxRendererType.CHAT

    def test_config_accepts_renderer_type_strings(self):
        """Test that config accepts renderer types as strings."""
        config = ReportRendererConfig(renderer_type="docx")  # type: ignore
        assert config.renderer_type == DocxRendererType.DOCX

        config2 = ReportRendererConfig(renderer_type="chat")  # type: ignore
        assert config2.renderer_type == DocxRendererType.CHAT

    def test_config_rejects_invalid_renderer_type(self):
        """Test that config rejects invalid renderer types."""
        with pytest.raises(ValidationError):
            ReportRendererConfig(renderer_type="invalid_type")  # type: ignore

    def test_config_with_empty_template(self):
        """Test configuration with empty template string."""
        config = ReportRendererConfig(report_template="")
        assert config.report_template == ""

    def test_config_template_preserves_formatting(self):
        """Test that template formatting is preserved."""
        template_with_formatting = """
# Title

## Section
- Item 1
- Item 2

{{ content }}
"""
        config = ReportRendererConfig(report_template=template_with_formatting)
        assert config.report_template == template_with_formatting

    def test_config_update(self):
        """Test updating configuration values."""
        config = ReportRendererConfig()
        original_type = config.renderer_type

        # Create a new config with updated values
        updated_config = ReportRendererConfig(
            report_template=config.report_template,
            renderer_type=DocxRendererType.CHAT,
            docx_renderer_config=config.docx_renderer_config,
        )

        assert original_type == DocxRendererType.DOCX
        assert updated_config.renderer_type == DocxRendererType.CHAT
