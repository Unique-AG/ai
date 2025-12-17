from logging import getLogger
from typing import Callable

from jinja2 import Template
from unique_toolkit import ChatService
from unique_toolkit._common.docx_generator import DocxGeneratorService

from unique_swot.services.citations import CitationManager
from unique_swot.services.generation.models.base import SWOTReportComponents
from unique_swot.services.report.config import DocxRendererType
from unique_swot.services.report.docx import (
    add_citation_footer,
    convert_markdown_to_docx,
)
from unique_swot.services.session import SwotAnalysisSessionConfig
from unique_swot.utils import convert_content_chunk_to_reference

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
    ):
        self._chat_service = chat_service
        self._docx_renderer = docx_renderer
        self._citation_manager = citation_manager
        self._renderer_type = renderer_type
        self._template_name = template_name

    def render_report(
        self,
        result: SWOTReportComponents,
        citation_fn: Callable[[str], str],
        executive_summary: str | None = None,
    ) -> str:
        # Render using the template
        markdown_report = Template(self._template_name).render(
            **result.model_dump(),
            executive_summary=executive_summary,
        )
        return citation_fn(markdown_report)

    def deliver_report(
        self,
        *,
        start_text: str,
        executive_summary: str,
        result: SWOTReportComponents,
        session_config: SwotAnalysisSessionConfig,
        docx_template_fields: dict[str, str],
        ingest_docx: bool,
        num_existing_references: int,
    ) -> str:
        """
        Delivers a SWOT analysis report to the chat.

        Args:
            session_config: The session configuration containing company info
            result: List of consolidated SWOT reports (one per component)
            docx_template_fields: The fields to be used in the DOCX template
            ingest_docx: Whether to ingest the DOCX file
        """

        markdown_report = self.render_report(
            result=result,
            citation_fn=lambda report: self._citation_manager.add_citations_to_report(
                report, self._renderer_type.value
            ),
            executive_summary=executive_summary,
        )

        citations = self._citation_manager.get_citations_for_docx()

        match self._renderer_type:
            case DocxRendererType.DOCX:
                self._deliver_docx_report(
                    start_text=start_text,
                    session_config=session_config,
                    markdown_report=markdown_report,
                    template_fields=docx_template_fields,
                    ingest_docx=ingest_docx,
                    citations=citations,
                    num_existing_references=num_existing_references,
                )
            case DocxRendererType.CHAT:
                self._deliver_markdown_report(
                    markdown_report=markdown_report,
                )
            case _:
                raise ValueError(f"Invalid renderer type: {self._renderer_type}")

        return markdown_report

    def _convert_consolidated_reports_to_markdown(
        self,
        consolidated_reports: SWOTReportComponents,
        markdown_jinja_template: str,
        processor: Callable[[str], str],
    ) -> str:
        """
        Converts a list of consolidated reports into a markdown report.

        Args:
            consolidated_reports: List of consolidated reports (one per component)
            markdown_jinja_template: The Jinja2 template for rendering
            processor: Function to process the markdown (e.g., add citations)

        Returns:
            Formatted markdown report
        """

        # Render using the template
        markdown_report = Template(markdown_jinja_template).render(
            **consolidated_reports.model_dump()
        )
        return processor(markdown_report)

    def _deliver_docx_report(
        self,
        *,
        start_text: str,
        markdown_report: str,
        template_fields: dict[str, str],
        session_config: SwotAnalysisSessionConfig,
        ingest_docx: bool,
        citations: list[str],
        num_existing_references: int,
    ) -> None:
        """Converts markdown to DOCX and delivers it as an attachment"""

        if citations:
            markdown_report = add_citation_footer(markdown_report, citations)

        # Convert markdown to DOCX
        docx_bytes = convert_markdown_to_docx(
            markdown_report, self._docx_renderer, template_fields
        )
        if docx_bytes is None:
            raise ValueError("Failed to convert markdown to DOCX")

        # Upload to chat
        document_name = (
            f"{session_config.company_listing.name} SWOT Analysis Report.docx"
        )
        content = self._chat_service.upload_to_chat_from_bytes(
            content=docx_bytes,
            content_name=document_name,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            skip_ingestion=not ingest_docx,
        )

        # Create content reference
        content_reference = convert_content_chunk_to_reference(
            content_or_chunk=content,
            sequence_number=num_existing_references,
        )

        # Modify assistant message
        self._chat_service.modify_assistant_message(
            message_id=self._chat_service.assistant_message_id,
            content=f"{start_text}\n\n Here is the full Swot Analysis report for {session_config.company_listing.name} in DOCX format <sup>{num_existing_references}</sup>.",
            references=[content_reference],
        )

        _LOGGER.info(
            f"Successfully delivered DOCX report for message {self._chat_service.assistant_message_id}"
        )

    def _deliver_markdown_report(
        self,
        *,
        markdown_report: str,
    ) -> None:
        """Delivers the markdown report directly to the chat"""
        references = self._citation_manager.get_references(
            message_id=self._chat_service.assistant_message_id
        )

        self._chat_service.modify_assistant_message(
            message_id=self._chat_service.assistant_message_id,
            content=markdown_report,
            references=references,
        )

        _LOGGER.info(
            f"Successfully delivered markdown report for message {self._chat_service.assistant_message_id}"
        )
