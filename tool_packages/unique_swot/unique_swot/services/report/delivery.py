from logging import getLogger

from unique_toolkit import ChatService
from unique_toolkit._common.docx_generator import DocxGeneratorService
from unique_toolkit.content import ContentReference

from unique_swot.services.citations import CitationManager
from unique_swot.services.report.config import DocxRendererType
from unique_swot.services.report.docx import (
    add_citation_footer,
    convert_markdown_to_docx,
)
from unique_swot.services.schemas import SWOTResult

_LOGGER = getLogger(__name__)


class ReportDeliveryService:
    """
    Handles the delivery of SWOT analysis reports to the chat.

    This service is responsible for:
    - Converting markdown reports to appropriate formats (DOCX/Markdown)
    - Uploading content to chat
    - Creating content references
    - Modifying assistant messages with the delivered content
    """

    def __init__(
        self,
        *,
        chat_service: ChatService,
        docx_renderer: DocxGeneratorService,
        citation_manager: CitationManager,
        renderer_type: DocxRendererType,
        template_name: str,
        message_id: str,
    ):
        self._chat_service = chat_service
        self._docx_renderer = docx_renderer
        self._citation_manager = citation_manager
        self._renderer_type = renderer_type
        self._message_id = message_id
        self._template_name = template_name

    def deliver_report(
        self,
        company_name: str,
        result: SWOTResult,
        docx_template_fields: dict[str, str],
    ) -> str:
        """
        Delivers a SWOT analysis report to the chat.

        Args:
            markdown_report: The markdown formatted report
            message_id: The ID of the assistant message to modify
            docx_template_fields: The fields to be used in the DOCX template
        """
        markdown_report = result.to_markdown_report(
            markdown_jinja_template=self._template_name,
            processor=lambda report: self._citation_manager.add_citations_to_report(
                report, self._renderer_type
            ),
        )
        citations = self._citation_manager.get_citations(self._renderer_type)

        match self._renderer_type:
            case DocxRendererType.DOCX:
                self._deliver_docx_report(
                    company_name=company_name,
                    markdown_report=markdown_report,
                    citations=citations,
                    template_fields=docx_template_fields,
                )
            case DocxRendererType.CHAT:
                self._deliver_markdown_report(
                    markdown_report=markdown_report,
                )
            case _:
                raise ValueError(f"Invalid renderer type: {self._renderer_type}")

        return markdown_report

    def _deliver_docx_report(
        self,
        *,
        markdown_report: str,
        citations: list[str] | None,
        template_fields: dict[str, str],
        company_name: str,
    ) -> None:
        """Converts markdown to DOCX and delivers it as an attachment"""

        if citations is not None:
            markdown_report = add_citation_footer(markdown_report, citations)

        # Convert markdown to DOCX
        docx_bytes = convert_markdown_to_docx(
            markdown_report, self._docx_renderer, template_fields
        )
        if docx_bytes is None:
            raise ValueError("Failed to convert markdown to DOCX")

        # Upload to chat
        content = self._chat_service.upload_to_chat_from_bytes(
            content=docx_bytes,
            content_name=f"{company_name} SWOT Analysis Report.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            skip_ingestion=True,
        )

        # Create content reference
        content_reference = self._create_content_reference(
            content_id=content.id,
            message_id=self._message_id,
        )

        # Modify assistant message
        self._chat_service.modify_assistant_message(
            message_id=self._message_id,
            content=f"Here is the {company_name} SWOT analysis report in DOCX format <sup>1</sup>.",
            references=[content_reference],
        )

        _LOGGER.info(
            f"Successfully delivered DOCX report for message {self._message_id}"
        )

    def _deliver_markdown_report(
        self,
        *,
        markdown_report: str,
    ) -> None:
        """Delivers the markdown report directly to the chat"""
        references = self._citation_manager.get_references(message_id=self._message_id)

        self._chat_service.modify_assistant_message(
            message_id=self._message_id,
            content=markdown_report,
            references=references,
        )

        _LOGGER.info(
            f"Successfully delivered markdown report for message {self._message_id}"
        )

    @staticmethod
    def _create_content_reference(
        content_id: str,
        message_id: str,
    ) -> ContentReference:
        """Creates a content reference for uploaded DOCX files"""
        return ContentReference(
            url=f"unique//content/{content_id}",
            source_id=content_id,
            message_id=message_id,
            name="swot_analysis_report.docx",
            sequence_number=1,
            source="SWOT-TOOL",
        )
