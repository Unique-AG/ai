"""
Citation management for SWOT reports with dual referencing system.

This module handles the transformation of citation placeholders in SWOT reports
into formatted references. It supports a two-level citation system:
1. Inline citations after bullet points: [bullet_chunk_X] -> [1], [2], etc.
2. Consolidated references section: [chunk_X] -> [1] with source details

Example transformation:
Input:
    - **Bold reasoning.** Details here [bullet_chunk_a], [bullet_chunk_b]
    - **More reasoning.** More details [bullet_chunk_c]

    **References:** [chunk_a], [chunk_b], [chunk_c]

Output (DOCX mode):
    - **Bold reasoning.** Details here [1], [2]
    - **More reasoning.** More details [3]

    **References:** [1] [Document Title: page 5], [2] [Document Title: page 7], [3] [Document Title: page 9]
"""

import re
from logging import getLogger

from unique_toolkit.content.schemas import ContentChunk, ContentReference

from unique_swot.services.collection.registry import ContentChunkRegistry
from unique_swot.services.report import DocxRendererType

_LOGGER = getLogger(__name__)

# Pattern to match consolidated citations in References section: [chunk_X]
consolidated_citation_pattern = r"\[chunk_([a-zA-Z0-9\-]+)\]"


class CitationManager:
    """
    Manages citation transformation and tracking for SWOT analysis reports.

    This class handles a dual-citation system where:
    1. Inline citations ([bullet_chunk_X]) appear after each bullet point
    2. Consolidated citations ([chunk_X]) appear in a References section

    The manager assigns sequential numbers to inline citations and then maps
    consolidated citations to include both the number and source information.

    Attributes:
        _content_chunk_registry: Registry to retrieve full chunk metadata
        _citations_map: Maps chunk IDs to formatted consolidated citations
        _inline_citations_map: Maps chunk IDs to numeric references [1], [2], etc.
        _content_chunks: List of referenced chunks for generating content references
        _citation_function: Function to format citations (DOCX or Chat mode)
    """

    def __init__(self, content_chunk_registry: ContentChunkRegistry):
        """
        Initialize the citation manager.

        Args:
            content_chunk_registry: Registry containing all content chunks
            activate_docx: If True, use DOCX citation format with titles and pages.
                          If False, use Chat format with superscript numbers.
        """
        self._content_chunk_registry = content_chunk_registry

        # Maps chunk IDs to their final formatted citations (e.g., "[1] [Title: page 5]")
        self._citations_map = {}

        self._citated_documents = {}

        # List of all referenced chunks for generating ContentReference objects
        self._content_chunks: list[ContentChunk] = []

    def add_citations_to_report(
        self, report: str, renderer_type: DocxRendererType
    ) -> str:
        """
        Main entry point to process all citations in a report.

        Process inline citations ([chunk_X]) to assign numbers

        The order is important: inline citations must be processed first to establish
        the numbering that consolidated citations will reference.

        Args:
            report: Raw report text with citation placeholders

        Returns:
            Fully formatted report with all citations transformed
        """
        report = self._handle_inline_citations(report, renderer_type)

        return report

    def _handle_inline_citations(
        self, report: str, renderer_type: DocxRendererType
    ) -> str:
        """
        Transform consolidated references into full citations with source info.

        Converts [chunk_X] -> [1] [Document Title: page 5]
        Links back to the inline citation numbers and adds source metadata.
        Retrieves full chunk information from the registry.

        Args:
            report: The report text containing [chunk_X] placeholders

        Returns:
            Report text with consolidated citations replaced by full references

        Example:
            Input:  "**References:** [chunk_a], [chunk_b]"
            Output: "**References:** [1] Annual Report: page 23, [2] [Earnings Call: page 45]"
        """
        # Find all consolidated citation IDs in the report
        citations = re.findall(consolidated_citation_pattern, report)

        for citation in citations:
            if citation in self._citations_map:
                # Citation already processed, reuse the formatted version
                replace_with = self._citations_map[citation]
            else:
                # Retrieve the full chunk metadata from the registry
                chunk = self._content_chunk_registry.retrieve(f"chunk_{citation}")

                if chunk is not None:
                    if renderer_type == DocxRendererType.DOCX:
                        replace_with = self._citation_in_docx(chunk)
                    else:
                        replace_with = self._citation_in_chat()

                    # Cache for future use and track for ContentReference generation
                    self._citations_map[citation] = replace_with
                    self._content_chunks.append(chunk)
                else:
                    # Chunk not found - log warning and leave placeholder
                    _LOGGER.warning(f"Chunk {citation} not found in registry")
                    replace_with = "[???]"

            # Replace the placeholder with the full citation
            report = report.replace(f"[chunk_{citation}]", replace_with)

        return report

    def _citation_in_docx(self, chunk: ContentChunk) -> str:
        """
        Format a citation for DOCX output with document title and page numbers.

        Args:
            chunk: The content chunk to format

        Returns:
            Formatted citation like "[Annual Report 2023: page 45, 46]"
        """
        title = _get_title(chunk)
        pages = _get_pages(chunk.start_page, chunk.end_page)
        document_reference_index = self._get_reference_index(title)

        return f"_[{document_reference_index}: p{pages}]_ "

    def _citation_in_chat(self) -> str:
        """
        Format a citation for Chat output with superscript numbers.

        Args:
            chunk: The content chunk to format

        Returns:
            Formatted citation like "<sup>1</sup>"
        """
        return f"<sup>{len(self._citations_map) + 1}</sup>"

    def get_citations(self, renderer_type: DocxRendererType) -> list[str] | None:
        """
        Append citations to the report.
        """
        if renderer_type == DocxRendererType.DOCX:
            return [
                f"[{index}] {title}" for title, index in self._citated_documents.items()
            ]

    def get_references(self, message_id: str) -> list[ContentReference]:
        """
        Generate ContentReference objects for all chunks used in the report.

        Converts internal chunk tracking into the format expected by the content system
        for displaying references in the UI.

        Args:
            message_id: ID of the message/report these references belong to

        Returns:
            List of ContentReference objects for UI display
        """
        return [
            _convert_content_chunk_to_content_reference(message_id, index, chunk)
            for index, chunk in enumerate(self._content_chunks)
        ]

    def get_referenced_content_chunks(self) -> list[ContentChunk]:
        """
        Get the raw list of all content chunks referenced in the report.

        Returns:
            List of ContentChunk objects that were cited
        """
        return self._content_chunks

    def _get_reference_index(self, title: str) -> int:
        """
        Get the reference index for a given title.
        """
        if title not in self._citated_documents:
            self._citated_documents[title] = len(self._citated_documents) + 1
        return self._citated_documents[title]


def _convert_content_chunk_to_content_reference(
    message_id: str, index: int, chunk: ContentChunk
) -> ContentReference:
    """
    Convert a ContentChunk into a ContentReference for UI display.

    Args:
        message_id: ID of the message these references belong to
        index: Sequential number of this reference (for ordering)
        chunk: The content chunk to convert

    Returns:
        ContentReference object with URL, title, pages, and metadata
    """
    url = f"unique//content/{chunk.id}"
    source_id = f"{chunk.id}_{chunk.chunk_id}"
    filename = _get_title(chunk)
    pages = _get_pages(chunk.start_page, chunk.end_page)
    title = f"{filename}: {pages}"
    return ContentReference(
        url=url,
        source_id=source_id,
        message_id=message_id,
        name=title,
        sequence_number=index,
        source="SWOT-TOOL",
    )


def _get_pages(start_page: int | None, end_page: int | None) -> str:
    """
    Format page number(s) for display in citations.

    Args:
        start_page: First page number (or None if no page info)
        end_page: Last page number (or None if single page)

    Returns:
        Formatted page string:
        - "" if no page info
        - "5" if single page
        - "5, 7" if page range
    """
    if start_page is None:
        return ""
    if end_page is None or end_page == start_page:
        return f"{start_page}"
    return f"{start_page}, {end_page}"


def _get_title(chunk: ContentChunk) -> str:
    return chunk.title or chunk.key or "Unknown Title"
