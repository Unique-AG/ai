from logging import getLogger
from typing import Callable

from jinja2 import Template
from unique_toolkit import ChatService
from unique_toolkit._common.docx_generator import DocxGeneratorService

from unique_swot.services.citations import CitationManager
from unique_swot.services.generation.models.base import SWOTReportComponents
from unique_swot.services.report.config import RendererType, ReportRendererConfig
from unique_swot.services.report.docx import (
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
        renderer_config: ReportRendererConfig,
    ):
        self._chat_service = chat_service
        self._docx_renderer = docx_renderer
        self._citation_manager = citation_manager
        self._renderer_config = renderer_config

    def render_report(
        self,
        citation_fn: Callable[[str], str],
        executive_summary: str | None = None,
        body: str | None = None,
    ) -> str:
        # Render using the template
        markdown_report = Template(
            self._renderer_config.report_structure_template
        ).render(
            executive_summary=executive_summary,
            body=body,
        )
        return citation_fn(markdown_report)

    def render_body(self, result: SWOTReportComponents) -> str:
        return Template(self._renderer_config.report_body_template).render(
            **result.model_dump(),
        )

    def deliver_report(
        self,
        *,
        executive_summary: str,
        body: str,
        session_config: SwotAnalysisSessionConfig,
        docx_template_fields: dict[str, str],
        ingest_docx: bool,
    ) -> str:
        """
        Delivers a SWOT analysis report to the chat.

        Args:
            session_config: The session configuration containing company info
            result: List of consolidated SWOT reports (one per component)
            docx_template_fields: The fields to be used in the DOCX template
            ingest_docx: Whether to ingest the DOCX file
        """

        renderer_type = self._renderer_config.renderer_type

        executive_summary, body = map(
            lambda content: self._citation_manager.map_citations_to_report(
                content, self._renderer_config.renderer_type
            ),
            [executive_summary, body],
        )

        number_of_citations = len(self._citation_manager.get_citations_for_docx())

        full_report = Template(self._renderer_config.report_structure_template).render(
            executive_summary=executive_summary,
            body=body,
            citations=self._citation_manager.get_citations_for_docx()
            if renderer_type == RendererType.DOCX
            else None,
        )

        match renderer_type:
            case RendererType.DOCX:
                self._deliver_docx_report(
                    session_config=session_config,
                    markdown_report=full_report,
                    template_fields=docx_template_fields,
                    ingest_docx=ingest_docx,
                    sequence_number=number_of_citations,
                )
            case RendererType.CHAT:
                self._deliver_markdown_report(
                    markdown_report=full_report,
                )
            case _:
                raise ValueError(f"Invalid renderer type: {renderer_type}")

        return full_report

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
        markdown_report: str,
        template_fields: dict[str, str],
        session_config: SwotAnalysisSessionConfig,
        ingest_docx: bool,
        sequence_number: int,
    ) -> None:
        """Converts markdown to DOCX and delivers it as an attachment"""

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
            sequence_number=sequence_number,
        )

        # Modify assistant message
        self._chat_service.modify_assistant_message(
            message_id=self._chat_service.assistant_message_id,
            content=f"Here is the full Swot Analysis report for {session_config.company_listing.name} in DOCX format <sup>{sequence_number}</sup>.",
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
