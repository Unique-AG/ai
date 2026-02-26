"""Tests for the ReportRendererConfig."""

from unique_swot.services.report.config import RendererType, ReportRendererConfig


def test_report_renderer_config_ingest_docx_report_default():
    """Test that ingest_docx_report has a default value of False."""
    config = ReportRendererConfig()

    # Verify the default value
    assert config.ingest_docx_report is False
    assert isinstance(config.ingest_docx_report, bool)


def test_report_renderer_config_ingest_docx_report_can_be_set():
    """Test that ingest_docx_report can be explicitly set to True."""
    config = ReportRendererConfig(ingest_docx_report=True)

    # Verify the value is set correctly
    assert config.ingest_docx_report is True


def test_report_renderer_config_has_field_description():
    """Test that ingest_docx_report field has a description."""
    # Get the field info from the model
    field_info = ReportRendererConfig.model_fields["ingest_docx_report"]

    # Verify the description exists and contains expected content
    assert field_info.description is not None
    assert isinstance(field_info.description, str)
    assert len(field_info.description) > 0
    # The description should mention follow-up questions and side view
    assert (
        "follow-up" in field_info.description.lower()
        or "side view" in field_info.description.lower()
    )


def test_report_renderer_config_has_required_fields():
    """Test that ReportRendererConfig has all required fields."""
    config = ReportRendererConfig()

    # Verify required fields exist
    assert hasattr(config, "renderer_type")
    assert hasattr(config, "report_structure_template")
    assert hasattr(config, "report_body_template")
    assert hasattr(config, "docx_renderer_config")
    assert hasattr(config, "ingest_docx_report")


def test_report_renderer_config_renderer_type_default():
    """Test that renderer_type has a default value."""
    config = ReportRendererConfig()

    # Verify renderer_type is set to DOCX by default
    assert config.renderer_type == RendererType.DOCX


def test_report_renderer_config_templates_are_strings():
    """Test that template fields are strings."""
    config = ReportRendererConfig()

    # Verify templates are strings
    assert isinstance(config.report_structure_template, str)
    assert isinstance(config.report_body_template, str)
