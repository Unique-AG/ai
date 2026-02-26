"""
Markdown processing utilities for deep research tool.

This module provides functions for extracting and processing markdown links
from research results, including conversion to ContentReference objects
and replacement with superscript notation.
"""

import logging
import re
from typing import Dict, NamedTuple

from unique_toolkit import ChatService, ContentService
from unique_toolkit._common.docx_generator import (
    pandoc_markdown_to_docx_async,
)
from unique_toolkit._common.referencing import get_all_ref_numbers, replace_ref_number
from unique_toolkit.content.schemas import ContentChunk, ContentReference

from unique_deep_research.config import DocxExportConfig
from unique_deep_research.unique_custom.citation import CitationMetadata

_LOGGER = logging.getLogger(__name__)


class MarkdownLink(NamedTuple):
    """Represents a markdown link with its text and URL."""

    text: str
    url: str
    full_match: str


def extract_markdown_links(text: str) -> list[MarkdownLink]:
    """
    Extract all markdown links from text.

    Supports both standard markdown links [text](url) and reference-style links.
    Based on patterns used throughout the codebase for markdown processing.

    Args:
        text: The text to extract links from

    Returns:
        List of MarkdownLink objects containing the link text, URL, and full match
    """
    links = []

    # Standard markdown links: [text](url)
    standard_link_pattern = r"\[([^\]]*)\]\(([^)]*)\)"

    for match in re.finditer(standard_link_pattern, text):
        link_text = match.group(1)
        url = match.group(2)
        full_match = match.group(0)

        # Skip image links (they start with !)
        start_pos = match.start()
        if start_pos == 0 or text[start_pos - 1] != "!":
            links.append(MarkdownLink(text=link_text, url=url, full_match=full_match))

    return links


def create_content_references_from_links(
    extracted_links: list[MarkdownLink], message_id: str = ""
) -> list[ContentReference]:
    """
    Create ContentReference objects from extracted markdown links.

    Args:
        extracted_links: List of MarkdownLink objects
        message_id: Message ID for the references

    Returns:
        List of ContentReference objects
    """
    references = []
    seen_urls = set()
    sequence_number = 1

    for link in extracted_links:
        # Skip duplicate URLs
        if link.url in seen_urls:
            continue
        seen_urls.add(link.url)

        # Create ContentReference with proper sequence numbering
        reference = ContentReference(
            message_id=message_id,
            name=link.text or f"Reference {sequence_number}",
            sequence_number=sequence_number,
            source="deep-research-links",
            source_id=link.url,
            url=link.url,
        )
        references.append(reference)
        sequence_number += 1

    return references


def create_content_references_and_chunks_from_links(
    extracted_links: list[MarkdownLink],
    tool_call_id: str = "",
    message_id: str = "",
) -> tuple[list[ContentReference], list[ContentChunk]]:
    """
    Create both ContentReference and ContentChunk objects from extracted links.

    This unified function creates both types of content objects from the same
    source data (the extracted links), ensuring perfect consistency between
    references and chunks. Both use the same logic but different naming conventions.

    Args:
        extracted_links: List of extracted markdown links
        tool_call_id: ID of the tool call for chunk identification
        message_id: Message ID for creating references

    Returns:
        Tuple of (content_references, content_chunks)
    """
    content_references = []
    content_chunks = []
    seen_urls = set()
    sequence_number = 1

    for i, link in enumerate(extracted_links):
        # Skip duplicate URLs for references but create chunks for all
        if link.url not in seen_urls:
            # Create ContentReference
            reference = ContentReference(
                message_id=message_id,
                name=link.text or f"Reference {sequence_number}",
                sequence_number=sequence_number,
                source="deep-research-links",
                source_id=link.url,
                url=link.url,
            )
            content_references.append(reference)
            seen_urls.add(link.url)
            sequence_number += 1

        # Create ContentChunk for each link (including duplicates for context)
        chunk = ContentChunk(
            id=f"deep-research-{tool_call_id}-{link.url}",
            chunk_id=f"dr-{link.url}",
            text=link.text,
            order=0,
            key=link.url,
            title="Deep Research Links",
            url=link.url,
        )
        content_chunks.append(chunk)

    return content_references, content_chunks


def replace_links_with_superscript_references(
    text: str, extracted_links: list[MarkdownLink]
) -> str:
    """
    Replace markdown links with superscript references.

    Args:
        text: The original text containing markdown links
        extracted_links: List of extracted markdown links

    Returns:
        Text with markdown links replaced by superscript references
    """
    processed_text = text
    url_to_reference_number = {}
    reference_counter = 1

    # Build URL to reference number mapping (avoiding duplicates)
    for link in extracted_links:
        if link.url not in url_to_reference_number:
            url_to_reference_number[link.url] = reference_counter
            reference_counter += 1

    # Replace each markdown link with superscript reference
    # Process in reverse order to avoid position shifts
    for link in reversed(extracted_links):
        reference_number = url_to_reference_number[link.url]

        # Replace the full markdown link with text + superscript
        replacement = f"<sup>{reference_number}</sup>"

        # Find and replace the specific occurrence
        processed_text = processed_text.replace(link.full_match, replacement, 1)

    return processed_text


def postprocess_research_result_complete(
    research_result: str, message_id: str = ""
) -> tuple[str, list[ContentReference]]:
    """
    Complete postprocessing pipeline for research results.

    This function:
    1. Extracts all markdown links from the research result
    2. Generates ContentReference objects from the links
    3. Replaces markdown URLs with superscript references

    Args:
        research_result: The research result text containing markdown links
        message_id: Message ID for creating references

    Returns:
        Tuple of (processed_text_with_superscripts, content_references)
    """
    if not research_result:
        return research_result, []

    # Step 1: Extract markdown links
    extracted_links = extract_markdown_links(research_result)

    if not extracted_links:
        return research_result, []

    # Step 2: Create ContentReferences from links
    content_references = create_content_references_from_links(
        extracted_links, message_id
    )

    # Step 3: Replace markdown links with superscript references
    processed_text = replace_links_with_superscript_references(
        research_result, extracted_links
    )

    return processed_text, content_references


def postprocess_research_result_with_chunks(
    research_result: str, tool_call_id: str = "", message_id: str = ""
) -> tuple[str, list[ContentReference], list[ContentChunk]]:
    """
    Complete postprocessing pipeline for research results including ContentChunks.

    This function:
    1. Extracts all markdown links from the research result
    2. Creates both ContentReference and ContentChunk objects from the same links
    3. Replaces markdown URLs with superscript references

    Args:
        research_result: The research result text containing markdown links
        tool_call_id: ID of the tool call for chunk identification
        message_id: Message ID for creating references

    Returns:
        Tuple of (processed_text_with_superscripts, content_references, content_chunks)
    """
    if not research_result:
        return research_result, [], []

    # Step 1: Extract markdown links
    extracted_links = extract_markdown_links(research_result)

    if not extracted_links:
        # No links found, return original text with empty references and chunks
        return research_result, [], []

    # Step 2: Create both references and chunks from the same link data
    content_references, content_chunks = (
        create_content_references_and_chunks_from_links(
            extracted_links, tool_call_id, message_id
        )
    )

    # Step 3: Replace markdown links with superscript references
    processed_text = replace_links_with_superscript_references(
        research_result, extracted_links
    )

    return processed_text, content_references, content_chunks


def extract_sup_citations(text: str) -> set[int]:
    """
    Extract all <sup>N</sup> citation numbers from text.

    Args:
        text: Text containing <sup>N</sup> citations

    Returns:
        Set of citation numbers found in the text
    """
    pattern = r"<sup>(\d+)</sup>"
    matches = re.findall(pattern, text)
    return {int(m) for m in matches}


def validate_and_map_citations(
    report: str, citation_registry: Dict[str, CitationMetadata]
) -> tuple[str, list[ContentReference]]:
    """
    Validate report citations against registry and generate references.

    This function:
    1. Extracts all <sup>N</sup> citations from the report
    2. Validates that all citation numbers exist in the registry
    3. Generates ContentReference objects for used citations
    4. Optionally removes invalid citations from the report

    Args:
        report: Final research report with <sup>N</sup> citations
        citation_registry: Dictionary mapping source_id to CitationMetadata

    Returns:
        Tuple of (processed_report, content_references)
    """
    # Extract all citation numbers used in report
    used_citations = extract_sup_citations(report)

    # Build reverse lookup: number -> metadata
    number_to_meta = {meta.number: meta for meta in citation_registry.values()}

    # Identify invalid citations (numbers not in registry)
    valid_numbers = set(number_to_meta.keys())
    invalid_citations = used_citations - valid_numbers

    if invalid_citations:
        _LOGGER.warning(f"Report contains {len(invalid_citations)} invalid citations")
        # Remove invalid citations from report
        processed_report = report
        for invalid_num in sorted(invalid_citations, reverse=True):
            processed_report = processed_report.replace(f"<sup>{invalid_num}</sup>", "")
    else:
        processed_report = report

    # Generate ContentReference objects for USED citations only
    references = []
    for num in sorted(used_citations & valid_numbers):
        meta = number_to_meta[num]
        references.append(
            ContentReference(
                name=meta.name,
                url=meta.url,
                sequence_number=meta.number,
                source=meta.type,
                source_id=meta.source_id,
            )
        )
    return processed_report, references


async def export_report_to_docx(
    report: str,
    references: list[ContentReference],
    config: DocxExportConfig,
    content_service: ContentService,
    chat_service: ChatService,
) -> tuple[str, ContentReference]:
    """Export the final report to a DOCX file and append it to the final report message."""

    template = None
    if config.template_content_id.strip() != "":
        template = content_service.download_content_to_bytes(config.template_content_id)

    reference_dict = {ref.sequence_number: ref for ref in references}

    docx_report = report
    if config.strip_markdown_dividers:
        docx_report = _remove_horizontal_rules(docx_report)

    docx_report = _remap_and_append_docx_references(
        report=docx_report, references=reference_dict
    )
    docx_bytes = await pandoc_markdown_to_docx_async(
        source=docx_report, template=template
    )

    content = await chat_service.upload_to_chat_from_bytes_async(
        content=docx_bytes,
        content_name="Deep Research Report",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        skip_ingestion=True,
        hide_in_chat=True,
    )

    next_reference_number = max(reference_dict, default=0) + 1

    reference = ContentReference(
        name="Deep Research Report",
        url=f"unique://content/{content.id}",
        sequence_number=next_reference_number,
        source="deep-research-report",
        source_id=content.id,
    )

    report = f"{report}\n\n> *Please use the following link to download the report:* <sup>{next_reference_number}</sup>"

    return report, reference


def _remap_and_append_docx_references(
    report: str, references: dict[int, ContentReference]
) -> str:
    """
    Remap <sup>N</sup> references to markdown links and append a Sources section.

    For each reference found in the report:
    - URL starting with https:// -> [[N]](url)
    - Otherwise -> [[N]](#source-N) (anchor to the Sources section)

    A Sources section is appended at the bottom with anchored entries.
    """
    ref_numbers = get_all_ref_numbers(text=report)
    if len(ref_numbers) == 0:
        return report

    used_references: list[tuple[int, ContentReference]] = []

    for num in ref_numbers:
        ref = references.get(num)
        if ref is None:
            report = replace_ref_number(text=report, ref_number=num, replacement="")
            continue

        used_references.append((num, ref))

        if ref.url.startswith("https://"):
            replacement = f"[[{num}]]({ref.url})"
        else:
            replacement = f"[{num}]"

        report = replace_ref_number(
            text=report, ref_number=num, replacement=replacement
        )

    if len(used_references) > 0:
        lines = [
            "",
            "---",
            "# Sources",
        ]

        for num, ref in used_references:
            if ref.url.startswith("https://"):
                lines.append(f"{num}. [{ref.name}]({ref.url})")
            else:
                lines.append(f"{num}. {ref.name}")

        report = report.rstrip() + "\n" + "\n".join(lines) + "\n"

    return report


_HORIZONTAL_RULE_PATTERN = re.compile(r"^\s*[-*_]{3,}\s*$", re.MULTILINE)


def _remove_horizontal_rules(text: str) -> str:
    """Remove markdown horizontal rule lines (---, ***, ___) from the input."""
    return _HORIZONTAL_RULE_PATTERN.sub("", text)
