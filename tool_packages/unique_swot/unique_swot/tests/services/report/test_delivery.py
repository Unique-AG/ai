"""Tests for the ReportDeliveryService."""

from unittest.mock import Mock, patch

import pytest

from unique_swot.services.generation.models.base import (
    SWOTReportComponents,
    SWOTReportComponentSection,
    SWOTReportSectionEntry,
)
from unique_swot.services.report.config import DocxRendererType
from unique_swot.services.report.delivery import ReportDeliveryService
from unique_swot.services.session.schema import (
    SwotAnalysisSessionConfig,
    UniqueCompanyListing,
)


def _make_report_components():
    """Helper to create test SWOTReportComponents."""
    return SWOTReportComponents(
        strengths=[
            SWOTReportComponentSection(
                h2="Market Position",
                entries=[
                    SWOTReportSectionEntry(
                        preview="Strong brand",
                        content="Strong brand recognition [chunk_a]",
                    )
                ],
            )
        ],
        weaknesses=[],
        opportunities=[],
        threats=[],
    )


def _make_session_config():
    """Helper to create test session config."""
    return SwotAnalysisSessionConfig(
        company_listing=UniqueCompanyListing(
            id=123.0,
            name="ACME Corp",
            display_name="ACME Corporation",
            country="US",
            tickers=[],
            source_url="https://example.com/acme",
            source="test",
        ),
        use_earnings_call=False,
        use_web_sources=False,
        earnings_call_start_date=None,
    )


def test_render_report_applies_citations(mock_citation_manager):
    """Test that render_report applies citations to the report."""
    mock_citation_manager.add_citations_to_report.return_value = "Report with citations"

    chat_service = Mock()
    docx_renderer = Mock()

    service = ReportDeliveryService(
        chat_service=chat_service,
        docx_renderer=docx_renderer,
        citation_manager=mock_citation_manager,
        renderer_type=DocxRendererType.CHAT,
        template_name="Template: {{strengths}}",
    )

    result = service.render_report(
        result=_make_report_components(),
        citation_fn=lambda x: x + " [cited]",
        executive_summary="Summary",
    )

    assert "[cited]" in result


def test_render_report_uses_template(mock_citation_manager):
    """Test that render_report uses the Jinja template."""
    mock_citation_manager.add_citations_to_report.return_value = "Processed"

    chat_service = Mock()
    docx_renderer = Mock()

    template = "Strengths: {% for s in strengths %}{{ s.h2 }}{% endfor %}"

    service = ReportDeliveryService(
        chat_service=chat_service,
        docx_renderer=docx_renderer,
        citation_manager=mock_citation_manager,
        renderer_type="chat",
        template_name=template,
    )

    result = service.render_report(
        result=_make_report_components(),
        citation_fn=lambda x: x,
    )

    assert "Market Position" in result


def test_deliver_report_docx_mode(mock_citation_manager):
    """Test delivering report in DOCX mode."""
    mock_citation_manager.add_citations_to_report.return_value = "Report [1]"
    mock_citation_manager.get_citations_for_docx.return_value = ["[1] Source"]

    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.upload_to_chat_from_bytes.return_value = Mock(
        id="uploaded_id", title="Report", key="report.docx"
    )

    docx_renderer = Mock()

    service = ReportDeliveryService(
        chat_service=chat_service,
        docx_renderer=docx_renderer,
        citation_manager=mock_citation_manager,
        renderer_type=DocxRendererType.DOCX,
        template_name="Template",
    )

    with patch(
        "unique_swot.services.report.delivery.convert_markdown_to_docx",
        return_value=b"docx bytes",
    ):
        service.deliver_report(
            start_text="Analysis complete",
            executive_summary="Summary",
            result=_make_report_components(),
            session_config=_make_session_config(),
            docx_template_fields={"title": "SWOT Report"},
            ingest_docx=True,
            num_existing_references=0,
        )

        # Verify DOCX was uploaded
        chat_service.upload_to_chat_from_bytes.assert_called_once()
        # Verify message was modified
        chat_service.modify_assistant_message.assert_called_once()


def test_deliver_report_chat_mode(mock_citation_manager):
    """Test delivering report in CHAT mode."""
    mock_citation_manager.add_citations_to_report.return_value = "Report with citations"
    mock_citation_manager.get_references.return_value = []

    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"

    docx_renderer = Mock()

    service = ReportDeliveryService(
        chat_service=chat_service,
        docx_renderer=docx_renderer,
        citation_manager=mock_citation_manager,
        renderer_type=DocxRendererType.CHAT,
        template_name="Template",
    )

    service.deliver_report(
        start_text="Analysis complete",
        executive_summary="Summary",
        result=_make_report_components(),
        session_config=_make_session_config(),
        docx_template_fields={"title": "SWOT Report"},
        ingest_docx=False,
        num_existing_references=0,
    )

    # Verify message was modified with markdown content
    chat_service.modify_assistant_message.assert_called_once()
    call_kwargs = chat_service.modify_assistant_message.call_args.kwargs
    assert "Report with citations" in call_kwargs["content"]


def test_deliver_report_docx_with_citations_footer(mock_citation_manager):
    """Test that DOCX report includes citation footer."""
    mock_citation_manager.add_citations_to_report.return_value = "Report"
    mock_citation_manager.get_citations_for_docx.return_value = [
        "[1] Document A",
        "[2] Document B",
    ]

    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.upload_to_chat_from_bytes.return_value = Mock(
        id="uploaded_id", title="Report", key="report.docx"
    )

    docx_renderer = Mock()

    service = ReportDeliveryService(
        chat_service=chat_service,
        docx_renderer=docx_renderer,
        citation_manager=mock_citation_manager,
        renderer_type=DocxRendererType.DOCX,
        template_name="Template",
    )

    with (
        patch(
            "unique_swot.services.report.delivery.convert_markdown_to_docx",
            return_value=b"docx bytes",
        ) as mock_convert,
        patch(
            "unique_swot.services.report.delivery.add_citation_footer",
            return_value="Report with footer",
        ) as mock_footer,
    ):
        service.deliver_report(
            start_text="Analysis complete",
            executive_summary="Summary",
            result=_make_report_components(),
            session_config=_make_session_config(),
            docx_template_fields={"title": "SWOT Report"},
            ingest_docx=True,
            num_existing_references=0,
        )

        # Verify citation footer was added
        mock_footer.assert_called_once()
        # Verify conversion was called with footer
        mock_convert.assert_called_once()


def test_deliver_report_skip_docx_ingestion(mock_citation_manager):
    """Test that DOCX ingestion can be skipped."""
    mock_citation_manager.add_citations_to_report.return_value = "Report"
    mock_citation_manager.get_citations_for_docx.return_value = []

    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.upload_to_chat_from_bytes.return_value = Mock(
        id="uploaded_id", title="Report", key="report.docx"
    )

    docx_renderer = Mock()

    service = ReportDeliveryService(
        chat_service=chat_service,
        docx_renderer=docx_renderer,
        citation_manager=mock_citation_manager,
        renderer_type=DocxRendererType.DOCX,
        template_name="Template",
    )

    with patch(
        "unique_swot.services.report.delivery.convert_markdown_to_docx",
        return_value=b"docx bytes",
    ):
        service.deliver_report(
            start_text="Analysis complete",
            executive_summary="Summary",
            result=_make_report_components(),
            session_config=_make_session_config(),
            docx_template_fields={"title": "SWOT Report"},
            ingest_docx=False,  # Skip ingestion
            num_existing_references=0,
        )

        # Verify upload was called with skip_ingestion=True
        call_kwargs = chat_service.upload_to_chat_from_bytes.call_args.kwargs
        assert call_kwargs["skip_ingestion"] is True


def test_deliver_report_with_existing_references(mock_citation_manager):
    """Test delivering report with existing references."""
    mock_citation_manager.add_citations_to_report.return_value = "Report"
    mock_citation_manager.get_citations_for_docx.return_value = []

    chat_service = Mock()
    chat_service.assistant_message_id = "msg_123"
    chat_service.upload_to_chat_from_bytes.return_value = Mock(
        id="uploaded_id", title="Report", key="report.docx"
    )

    docx_renderer = Mock()

    service = ReportDeliveryService(
        chat_service=chat_service,
        docx_renderer=docx_renderer,
        citation_manager=mock_citation_manager,
        renderer_type=DocxRendererType.DOCX,
        template_name="Template",
    )

    with patch(
        "unique_swot.services.report.delivery.convert_markdown_to_docx",
        return_value=b"docx bytes",
    ):
        service.deliver_report(
            start_text="Analysis complete",
            executive_summary="Summary",
            result=_make_report_components(),
            session_config=_make_session_config(),
            docx_template_fields={"title": "SWOT Report"},
            ingest_docx=True,
            num_existing_references=5,  # Existing references
        )

        # Verify reference number is used in message
        call_kwargs = chat_service.modify_assistant_message.call_args.kwargs
        assert "<sup>5</sup>" in call_kwargs["content"]


def test_deliver_report_invalid_renderer_type_raises(mock_citation_manager):
    """Test that invalid renderer type raises ValueError."""
    mock_citation_manager.add_citations_to_report.return_value = "Report"

    chat_service = Mock()
    docx_renderer = Mock()

    # Create service with valid enum, then mock the enum value to trigger error
    service = ReportDeliveryService(
        chat_service=chat_service,
        docx_renderer=docx_renderer,
        citation_manager=mock_citation_manager,
        renderer_type=DocxRendererType.DOCX,
        template_name="Template",
    )

    # Simulate invalid renderer type by patching the internal value
    service._renderer_type = Mock()
    service._renderer_type.value = "invalid"

    with pytest.raises(ValueError):
        service.deliver_report(
            start_text="Analysis complete",
            executive_summary="Summary",
            result=_make_report_components(),
            session_config=_make_session_config(),
            docx_template_fields={"title": "SWOT Report"},
            ingest_docx=True,
            num_existing_references=0,
        )
