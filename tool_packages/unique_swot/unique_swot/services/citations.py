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
from typing import Callable

from unique_toolkit.content.schemas import ContentChunk, ContentReference

from unique_swot.services.collection.registry import ContentChunkRegistry
from unique_swot.services.report import DocxRendererType

_LOGGER = getLogger(__name__)

# Pattern to match inline citations in bullet points: [bullet_chunk_X]
inline_citation_pattern = r"\[bullet_chunk_([a-zA-Z0-9\-]+)\]"

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

        # Maps chunk IDs to their numeric references (e.g., "1" -> "[1]")
        self._inline_citations_map = {}

        # List of all referenced chunks for generating ContentReference objects
        self._content_chunks: list[ContentChunk] = []

    def _handle_inline_citations(self, report: str) -> str:
        """
        Transform inline bullet-level citations into numeric references.

        Converts [bullet_chunk_X] -> [1], [bullet_chunk_Y] -> [2], etc.
        Assigns sequential numbers in order of first appearance.
        Stores the mapping for later use in consolidated citations.

        Args:
            report: The report text containing [bullet_chunk_X] placeholders

        Returns:
            Report text with inline citations replaced by numeric references

        Example:
            Input:  "Details here [bullet_chunk_a], [bullet_chunk_b]"
            Output: "Details here [1], [2]"
        """
        # Find all inline citation IDs in the report
        citations = re.findall(inline_citation_pattern, report)

        for citation in citations:
            if citation in self._inline_citations_map:
                # Citation already seen, reuse the same number
                replace_with = self._inline_citations_map[citation]
            else:
                # New citation, assign next sequential number
                replace_with = f"[{len(self._inline_citations_map) + 1}]"
                self._inline_citations_map[citation] = replace_with

            # Replace the placeholder with the numeric reference
            report = report.replace(f"[bullet_chunk_{citation}]", replace_with)

        return report

    def _handle_consolidated_citations(
        self, report: str, citation_function: Callable[[ContentChunk], str]
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
                    # Get the numeric reference that was assigned during inline processing
                    prefix = self._inline_citations_map.get(citation, "[?]")

                    # Format the source information (title, pages, etc.)
                    suffix = citation_function(chunk)

                    # Combine: [1] [Document Title: page 5]
                    replace_with = f"{prefix} {suffix}"

                    # Cache for future use and track for ContentReference generation
                    self._citations_map[citation] = replace_with
                    self._content_chunks.append(chunk)
                else:
                    # Chunk not found - log warning and leave placeholder
                    _LOGGER.warning(f"Chunk {citation} not found in registry")
                    replace_with = f"[chunk_{citation}]"

            # Replace the placeholder with the full citation
            report = report.replace(f"[chunk_{citation}]", replace_with)

        return report

    def add_citations_to_report(
        self, report: str, renderer_type: DocxRendererType
    ) -> str:
        """
        Main entry point to process all citations in a report.

        Performs a two-pass transformation:
        1. First pass: Process inline citations ([bullet_chunk_X]) to assign numbers
        2. Second pass: Process consolidated citations ([chunk_X]) to add source info

        The order is important: inline citations must be processed first to establish
        the numbering that consolidated citations will reference.

        Args:
            report: Raw report text with citation placeholders

        Returns:
            Fully formatted report with all citations transformed
        """
        match renderer_type:
            case DocxRendererType.DOCX:
                citation_function = self._citation_in_docx
            case DocxRendererType.CHAT:
                citation_function = self._citation_in_chat
            case _:
                raise ValueError(f"Invalid renderer type: {renderer_type}")

        # First pass: Assign numbers to inline citations
        report = self._handle_inline_citations(report)

        # Second pass: Add full source information to consolidated citations
        report = self._handle_consolidated_citations(report, citation_function)

        return report

    def _citation_in_docx(self, chunk: ContentChunk) -> str:
        """
        Format a citation for DOCX output with document title and page numbers.

        Args:
            chunk: The content chunk to format

        Returns:
            Formatted citation like "[Annual Report 2023: page 45, 46]"
        """
        title = chunk.title or chunk.key or "Unknown Title"
        pages = _get_pages(chunk.start_page, chunk.end_page)
        title_with_pages: str = f"{title}: {pages}"
        return f"{title_with_pages}"

    def _citation_in_chat(self, chunk: ContentChunk) -> str:
        """
        Format a citation for Chat output with superscript numbers.

        Args:
            chunk: The content chunk to format

        Returns:
            Formatted citation like "<sup>1</sup>"
        """
        return f"<sup>{len(self._citations_map) + 1}</sup>"

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
    filename = chunk.title or chunk.key or "Unknown Title"
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
