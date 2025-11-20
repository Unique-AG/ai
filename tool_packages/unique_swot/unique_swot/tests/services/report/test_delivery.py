"""Comprehensive tests for ReportDeliveryService."""

from unittest.mock import Mock

import pytest
from unique_toolkit.content import ContentReference

from unique_swot.services.citations import CitationManager
from unique_swot.services.report.config import DocxRendererType
from unique_swot.services.report.delivery import ReportDeliveryService
from unique_swot.services.schemas import SWOTOperation, SWOTResult, SWOTStepResult


# Module-level fixtures (shared across all test classes)
@pytest.fixture
def mock_chat_service():
    """Create a mock chat service."""
    service = Mock()
    service.upload_to_chat_from_bytes.return_value = Mock(id="content_123")
    service.modify_assistant_message.return_value = None
    return service


@pytest.fixture
def mock_docx_renderer():
    """Create a mock DOCX renderer."""
    renderer = Mock()
    renderer.parse_markdown_to_list_content_fields.return_value = []
    renderer.generate_from_template.return_value = b"fake docx bytes"
    return renderer


@pytest.fixture
def mock_citation_manager():
    """Create a mock citation manager."""
    manager = Mock(spec=CitationManager)
    manager.add_citations_to_report.side_effect = (
        lambda report, renderer_type: f"cited: {report}"
    )
    manager.get_citations.return_value = ["[1] Test Citation"]
    manager.get_references.return_value = [
        ContentReference(
            url="unique//content/123",
            source_id="123_456",
            message_id="msg_123",
            name="Test Doc: 1",
            sequence_number=0,
            source="SWOT-TOOL",
        )
    ]
    return manager


class TestReportDeliveryService:
    """Test cases for ReportDeliveryService class."""

    @pytest.fixture
    def sample_swot_result(self):
        """Create a sample SWOT result."""
        return SWOTResult(
            objective="Test SWOT Analysis",
            strengths=SWOTStepResult(
                operation=SWOTOperation.GENERATE,
                modify_instruction=None,
                result="Strong brand [bullet_chunk_a]",
            ),
            weaknesses=SWOTStepResult(
                operation=SWOTOperation.GENERATE,
                modify_instruction=None,
                result="Limited resources",
            ),
            opportunities=SWOTStepResult(
                operation=SWOTOperation.NOT_REQUESTED,
                modify_instruction=None,
                result="",
            ),
            threats=SWOTStepResult(
                operation=SWOTOperation.NOT_REQUESTED,
                modify_instruction=None,
                result="",
            ),
        )

    def test_initialization(
        self, mock_chat_service, mock_docx_renderer, mock_citation_manager
    ):
        """Test ReportDeliveryService initialization."""
        service = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.DOCX,
            template_name="template.j2",
            message_id="msg_123",
        )

        assert service._chat_service == mock_chat_service
        assert service._docx_renderer == mock_docx_renderer
        assert service._citation_manager == mock_citation_manager
        assert service._renderer_type == DocxRendererType.DOCX
        assert service._message_id == "msg_123"

    def test_deliver_docx_report_success(
        self,
        mock_chat_service,
        mock_docx_renderer,
        mock_citation_manager,
        sample_swot_result,
    ):
        """Test successful DOCX report delivery."""
        service = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.DOCX,
            template_name="# {{ objective }}",
            message_id="msg_123",
        )

        result = service.deliver_report(
            company_name="Test Company",
            result=sample_swot_result,
            docx_template_fields={
                "title": "SWOT Report",
                "date": "2024-01-01",
            },
        )

        # Verify citation processing
        mock_citation_manager.add_citations_to_report.assert_called_once()

        # Verify DOCX conversion
        mock_docx_renderer.parse_markdown_to_list_content_fields.assert_called_once()
        mock_docx_renderer.generate_from_template.assert_called_once()

        # Verify upload to chat
        mock_chat_service.upload_to_chat_from_bytes.assert_called_once()
        upload_call = mock_chat_service.upload_to_chat_from_bytes.call_args
        assert (
            upload_call[1]["content_name"] == "Test Company SWOT Analysis Report.docx"
        )
        assert upload_call[1]["skip_ingestion"] is True

        # Verify message modification
        mock_chat_service.modify_assistant_message.assert_called_once()
        modify_call = mock_chat_service.modify_assistant_message.call_args
        assert modify_call[1]["message_id"] == "msg_123"
        assert "Test Company" in modify_call[1]["content"]
        assert "SWOT analysis report" in modify_call[1]["content"]
        assert len(modify_call[1]["references"]) == 1

        # Verify return value
        assert isinstance(result, str)
        assert "cited:" in result

    def test_deliver_chat_report_success(
        self,
        mock_chat_service,
        mock_docx_renderer,
        mock_citation_manager,
        sample_swot_result,
    ):
        """Test successful Chat markdown report delivery."""
        service = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.CHAT,
            template_name="# {{ objective }}",
            message_id="msg_123",
        )

        result = service.deliver_report(
            company_name="Test Company",
            result=sample_swot_result,
            docx_template_fields={},
        )

        # Verify citation processing
        mock_citation_manager.add_citations_to_report.assert_called_once()

        # Verify DOCX conversion NOT called
        mock_docx_renderer.parse_markdown_to_list_content_fields.assert_not_called()
        mock_docx_renderer.generate_from_template.assert_not_called()

        # Verify no upload (markdown goes directly to message)
        mock_chat_service.upload_to_chat_from_bytes.assert_not_called()

        # Verify message modification with references
        mock_chat_service.modify_assistant_message.assert_called_once()
        modify_call = mock_chat_service.modify_assistant_message.call_args
        assert modify_call[1]["message_id"] == "msg_123"
        assert "cited:" in modify_call[1]["content"]
        assert len(modify_call[1]["references"]) == 1

        # Verify return value
        assert isinstance(result, str)

    def test_deliver_docx_report_no_renderer(
        self, mock_chat_service, mock_citation_manager, sample_swot_result
    ):
        """Test DOCX delivery fails when renderer is not configured."""
        service = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=None,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.DOCX,
            template_name="# {{ objective }}",
            message_id="msg_123",
        )

        with pytest.raises(AttributeError):
            service.deliver_report(
                company_name="Test Company",
                result=sample_swot_result,
                docx_template_fields={},
            )

    def test_deliver_docx_report_conversion_fails(
        self,
        mock_chat_service,
        mock_docx_renderer,
        mock_citation_manager,
        sample_swot_result,
    ):
        """Test DOCX delivery fails when conversion returns None."""
        mock_docx_renderer.generate_from_template.return_value = None

        service = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.DOCX,
            template_name="# {{ objective }}",
            message_id="msg_123",
        )

        with pytest.raises(ValueError, match="Failed to convert markdown to DOCX"):
            service.deliver_report(
                company_name="Test Company",
                result=sample_swot_result,
                docx_template_fields={},
            )

    def test_deliver_report_invalid_renderer_type(
        self,
        mock_chat_service,
        mock_docx_renderer,
        mock_citation_manager,
        sample_swot_result,
    ):
        """Test delivery fails with invalid renderer type."""
        service = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type="invalid_type",  # type: ignore
            template_name="# {{ objective }}",
            message_id="msg_123",
        )

        with pytest.raises(ValueError, match="Invalid renderer type"):
            service.deliver_report(
                company_name="Test Company",
                result=sample_swot_result,
                docx_template_fields={},
            )

    def test_create_content_reference(self):
        """Test _create_content_reference static method."""
        reference = ReportDeliveryService._create_content_reference(
            content_id="test_content_123",
            message_id="test_msg_456",
        )

        assert isinstance(reference, ContentReference)
        assert reference.url == "unique//content/test_content_123"
        assert reference.source_id == "test_content_123"
        assert reference.message_id == "test_msg_456"
        assert reference.name == "swot_analysis_report.docx"
        assert reference.sequence_number == 1
        assert reference.source == "SWOT-TOOL"

    def test_deliver_docx_report_with_multiple_references(
        self,
        mock_chat_service,
        mock_docx_renderer,
        mock_citation_manager,
        sample_swot_result,
    ):
        """Test DOCX delivery creates correct content reference structure."""
        service = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.DOCX,
            template_name="# {{ objective }}",
            message_id="msg_123",
        )

        service.deliver_report(
            company_name="Test Company",
            result=sample_swot_result,
            docx_template_fields={"title": "Test", "date": "2024-01-01"},
        )

        # Verify the reference structure passed to modify_assistant_message
        modify_call = mock_chat_service.modify_assistant_message.call_args
        references = modify_call[1]["references"]

        assert len(references) == 1
        assert references[0].name == "swot_analysis_report.docx"
        assert references[0].sequence_number == 1

    def test_deliver_chat_report_with_custom_template(
        self,
        mock_chat_service,
        mock_docx_renderer,
        mock_citation_manager,
        sample_swot_result,
    ):
        """Test Chat delivery with custom template."""
        custom_template = """
# SWOT Analysis: {{ objective }}

## Strengths
{{ strengths.result }}

## Weaknesses
{{ weaknesses.result }}
"""
        service = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.CHAT,
            template_name=custom_template,
            message_id="msg_123",
        )

        _ = service.deliver_report(
            company_name="Test Company",
            result=sample_swot_result,
            docx_template_fields={},
        )

        # Verify the markdown was processed
        mock_citation_manager.add_citations_to_report.assert_called_once()
        call_args = mock_citation_manager.add_citations_to_report.call_args
        markdown_content = call_args[0][0]

        assert "Test SWOT Analysis" in markdown_content
        assert "Strong brand" in markdown_content

    def test_deliver_report_processes_citations_correctly(
        self,
        mock_chat_service,
        mock_docx_renderer,
        mock_citation_manager,
        sample_swot_result,
    ):
        """Test that citations are processed with correct renderer type."""
        # Test DOCX mode
        service_docx = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.DOCX,
            template_name="# {{ objective }}",
            message_id="msg_123",
        )

        service_docx.deliver_report(
            company_name="Test Company",
            result=sample_swot_result,
            docx_template_fields={},
        )

        # Verify DOCX renderer type was passed
        call_args = mock_citation_manager.add_citations_to_report.call_args
        assert call_args[0][1] == DocxRendererType.DOCX

        # Reset mock
        mock_citation_manager.reset_mock()

        # Test CHAT mode
        service_chat = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.CHAT,
            template_name="# {{ objective }}",
            message_id="msg_123",
        )

        service_chat.deliver_report(
            company_name="Test Company",
            result=sample_swot_result,
            docx_template_fields={},
        )

        # Verify CHAT renderer type was passed
        call_args = mock_citation_manager.add_citations_to_report.call_args
        assert call_args[0][1] == DocxRendererType.CHAT


class TestReportDeliveryIntegration:
    """Integration tests for report delivery flow."""

    @pytest.fixture
    def full_swot_result(self):
        """Create a complete SWOT result with all sections."""
        return SWOTResult(
            objective="Complete Market Analysis",
            strengths=SWOTStepResult(
                operation=SWOTOperation.GENERATE,
                modify_instruction=None,
                result="- Strong brand [bullet_chunk_a]\n- Market leader [bullet_chunk_b]",
            ),
            weaknesses=SWOTStepResult(
                operation=SWOTOperation.GENERATE,
                modify_instruction=None,
                result="- Limited resources [bullet_chunk_c]\n- High costs [bullet_chunk_d]",
            ),
            opportunities=SWOTStepResult(
                operation=SWOTOperation.GENERATE,
                modify_instruction=None,
                result="- New markets [bullet_chunk_e]\n- Technology trends [bullet_chunk_f]",
            ),
            threats=SWOTStepResult(
                operation=SWOTOperation.GENERATE,
                modify_instruction=None,
                result="- Competition [bullet_chunk_g]\n- Regulation [bullet_chunk_h]",
            ),
        )

    def test_full_report_generation_docx(
        self,
        mock_chat_service,
        mock_docx_renderer,
        mock_citation_manager,
        full_swot_result,
    ):
        """Test complete report generation in DOCX mode."""
        service = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.DOCX,
            template_name="# {{ objective }}\n\n{{ strengths.result }}\n{{ weaknesses.result }}",
            message_id="msg_123",
        )

        result = service.deliver_report(
            company_name="Test Company",
            result=full_swot_result,
            docx_template_fields={
                "title": "Q4 2024 SWOT Analysis",
                "date": "2024-12-31",
            },
        )

        # Verify all components were called
        assert mock_citation_manager.add_citations_to_report.called
        assert mock_docx_renderer.parse_markdown_to_list_content_fields.called
        assert mock_docx_renderer.generate_from_template.called
        assert mock_chat_service.upload_to_chat_from_bytes.called
        assert mock_chat_service.modify_assistant_message.called

        # Verify the markdown report was returned
        assert isinstance(result, str)
        assert "cited:" in result

    def test_full_report_generation_chat(
        self,
        mock_chat_service,
        mock_docx_renderer,
        mock_citation_manager,
        full_swot_result,
    ):
        """Test complete report generation in Chat mode."""
        service = ReportDeliveryService(
            chat_service=mock_chat_service,
            docx_renderer=mock_docx_renderer,
            citation_manager=mock_citation_manager,
            renderer_type=DocxRendererType.CHAT,
            template_name="# {{ objective }}\n\n{{ strengths.result }}",
            message_id="msg_123",
        )

        result = service.deliver_report(
            company_name="Test Company",
            result=full_swot_result,
            docx_template_fields={},
        )

        # Verify citation processing
        assert mock_citation_manager.add_citations_to_report.called
        assert mock_citation_manager.get_references.called

        # Verify DOCX NOT used in chat mode
        assert not mock_docx_renderer.parse_markdown_to_list_content_fields.called
        assert not mock_chat_service.upload_to_chat_from_bytes.called

        # Verify message modification with markdown
        assert mock_chat_service.modify_assistant_message.called
        assert isinstance(result, str)
