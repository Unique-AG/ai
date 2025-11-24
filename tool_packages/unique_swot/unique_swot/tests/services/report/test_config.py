"""Tests for report configuration."""

import pytest

from unique_swot.services.report.config import (
    DocxGeneratorConfig,
    DocxRendererType,
    ReportRendererConfig,
)


class TestDocxRendererType:
    """Test cases for DocxRendererType enum."""

    def test_docx_renderer_type_membership(self):
        """Test DocxRendererType enum membership."""
        assert "docx" in DocxRendererType
        assert "chat" in DocxRendererType

    def test_docx_renderer_type_iteration(self):
        """Test iteration over DocxRendererType values."""
        types = list(DocxRendererType)
        assert len(types) == 2
        assert DocxRendererType.DOCX in types
        assert DocxRendererType.CHAT in types


class TestDocxGeneratorConfig:
    """Test cases for DocxGeneratorConfig model."""

    def test_docx_generator_config_can_be_instantiated(self):
        """Test that DocxGeneratorConfig can be instantiated."""
        # DocxGeneratorConfig is from unique_toolkit, just verify it can be created
        config = DocxGeneratorConfig()
        assert config is not None
        assert hasattr(config, "template_content_id")

    def test_docx_generator_config_with_template_id(self):
        """Test creating DocxGeneratorConfig with custom template ID."""
        config = DocxGeneratorConfig(template_content_id="template_123")

        # Verify custom value is set correctly
        assert config.template_content_id == "template_123"


class TestReportRendererConfig:
    """Test cases for ReportRendererConfig model."""

    def test_report_renderer_config_defaults(self):
        """Test default values for ReportRendererConfig."""
        config = ReportRendererConfig()

        assert config.renderer_type == DocxRendererType.DOCX
        assert isinstance(config.report_template, str)
        assert len(config.report_template) > 0
        assert isinstance(config.docx_renderer_config, DocxGeneratorConfig)
        assert config.ingest_docx_report is True  # New field defaults to True

    def test_report_renderer_config_with_custom_renderer_type(self):
        """Test creating ReportRendererConfig with CHAT renderer type."""
        config = ReportRendererConfig(renderer_type=DocxRendererType.CHAT)

        assert config.renderer_type == DocxRendererType.CHAT
        assert isinstance(config.report_template, str)

    def test_report_renderer_config_with_custom_template(self):
        """Test creating ReportRendererConfig with custom template."""
        config = ReportRendererConfig(report_template="custom_template.j2")

        assert config.report_template == "custom_template.j2"
        assert config.renderer_type == DocxRendererType.DOCX

    def test_report_renderer_config_with_docx_config(self):
        """Test creating ReportRendererConfig with custom DOCX config."""
        docx_config = DocxGeneratorConfig(template_content_id="custom_123")
        config = ReportRendererConfig(docx_renderer_config=docx_config)

        assert config.docx_renderer_config.template_content_id == "custom_123"

    def test_report_renderer_config_ingest_docx_true(self):
        """Test ReportRendererConfig with ingest_docx_report=True."""
        config = ReportRendererConfig(ingest_docx_report=True)

        assert config.ingest_docx_report is True

    def test_report_renderer_config_ingest_docx_false(self):
        """Test ReportRendererConfig with ingest_docx_report=False."""
        config = ReportRendererConfig(ingest_docx_report=False)

        assert config.ingest_docx_report is False

    def test_report_renderer_config_complete(self):
        """Test creating a complete ReportRendererConfig with all fields."""
        docx_config = DocxGeneratorConfig(template_content_id="template_456")
        config = ReportRendererConfig(
            renderer_type=DocxRendererType.DOCX,
            report_template="comprehensive_report.j2",
            docx_renderer_config=docx_config,
            ingest_docx_report=False,
        )

        assert config.renderer_type == DocxRendererType.DOCX
        assert config.report_template == "comprehensive_report.j2"
        assert config.docx_renderer_config.template_content_id == "template_456"
        assert config.ingest_docx_report is False

    def test_report_renderer_config_model_dump(self):
        """Test serializing ReportRendererConfig to dict."""
        config = ReportRendererConfig(
            renderer_type=DocxRendererType.CHAT, ingest_docx_report=False
        )
        data = config.model_dump()

        assert "renderer_type" in data
        assert "report_template" in data
        assert "docx_renderer_config" in data
        assert "ingest_docx_report" in data
        assert data["ingest_docx_report"] is False

    def test_report_renderer_config_model_validate(self):
        """Test validating ReportRendererConfig from dict."""
        data = {
            "renderer_type": "docx",
            "report_template": "test.j2",
            "docx_renderer_config": {
                "template_content_id": "test_123",
            },
            "ingest_docx_report": False,
        }

        config = ReportRendererConfig.model_validate(data)

        assert config.renderer_type == DocxRendererType.DOCX
        assert config.report_template == "test.j2"
        assert config.docx_renderer_config.template_content_id == "test_123"
        assert config.ingest_docx_report is False


class TestReportRendererConfigIntegration:
    """Integration tests for ReportRendererConfig."""

    @pytest.mark.parametrize(
        "renderer_type,ingest_docx,expected_ingest",
        [
            (DocxRendererType.DOCX, True, True),
            (DocxRendererType.DOCX, False, False),
            (DocxRendererType.CHAT, True, True),
            (DocxRendererType.CHAT, False, False),
        ],
    )
    def test_renderer_type_with_ingest_combinations(
        self, renderer_type, ingest_docx, expected_ingest
    ):
        """Test various combinations of renderer type and ingest settings."""
        config = ReportRendererConfig(
            renderer_type=renderer_type, ingest_docx_report=ingest_docx
        )

        assert config.renderer_type == renderer_type
        assert config.ingest_docx_report == expected_ingest

    def test_default_config_for_docx_workflow(self):
        """Test that default config works for typical DOCX workflow."""
        config = ReportRendererConfig()

        # Default should be DOCX renderer with ingestion enabled
        assert config.renderer_type == DocxRendererType.DOCX
        assert config.ingest_docx_report is True
        assert config.docx_renderer_config is not None

    def test_config_for_chat_workflow_no_ingestion(self):
        """Test config for chat workflow without ingestion."""
        config = ReportRendererConfig(
            renderer_type=DocxRendererType.CHAT, ingest_docx_report=False
        )

        # Chat renderer shouldn't need DOCX config, but it should still exist
        assert config.renderer_type == DocxRendererType.CHAT
        assert config.ingest_docx_report is False

    def test_config_serialization_roundtrip(self):
        """Test that config can be serialized and deserialized without loss."""
        original_config = ReportRendererConfig(
            renderer_type=DocxRendererType.DOCX,
            report_template="roundtrip.j2",
            ingest_docx_report=False,
            docx_renderer_config=DocxGeneratorConfig(
                template_content_id="roundtrip_123"
            ),
        )

        # Serialize
        data = original_config.model_dump()

        # Deserialize
        restored_config = ReportRendererConfig.model_validate(data)

        # Verify equality
        assert restored_config.renderer_type == original_config.renderer_type
        assert restored_config.report_template == original_config.report_template
        assert restored_config.ingest_docx_report == original_config.ingest_docx_report
        assert (
            restored_config.docx_renderer_config.template_content_id
            == original_config.docx_renderer_config.template_content_id
        )
