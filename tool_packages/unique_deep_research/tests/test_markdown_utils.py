"""
Unit tests for markdown_utils.py module.
"""

import pytest
from unique_toolkit.content.schemas import ContentReference

from unique_deep_research.markdown_utils import (
    MarkdownLink,
    _remap_and_append_docx_references,
    _remove_horizontal_rules,
    create_content_references_and_chunks_from_links,
    create_content_references_from_links,
    extract_markdown_links,
    extract_sup_citations,
    postprocess_research_result_complete,
    postprocess_research_result_with_chunks,
    replace_links_with_superscript_references,
    validate_and_map_citations,
)
from unique_deep_research.unique_custom.citation import CitationMetadata


@pytest.mark.ai
def test_extract_markdown_links__finds_standard_links__in_text() -> None:
    """
    Purpose: Verify extract_markdown_links finds standard markdown links.
    Why this matters: Core functionality for extracting links from research results.
    Setup summary: Provide text with markdown links and verify extraction.
    """
    # Arrange
    text = "Check out [OpenAI](https://openai.com) and [Google](https://google.com)"

    # Act
    links = extract_markdown_links(text)

    # Assert
    assert len(links) == 2
    assert links[0].text == "OpenAI"
    assert links[0].url == "https://openai.com"
    assert links[1].text == "Google"
    assert links[1].url == "https://google.com"


@pytest.mark.ai
def test_extract_markdown_links__ignores_image_links__with_exclamation_prefix() -> None:
    """
    Purpose: Verify extract_markdown_links ignores image links.
    Why this matters: Image links should not be treated as citation sources.
    Setup summary: Provide text with image links and verify they are ignored.
    """
    # Arrange
    text = "Here's an image ![alt](image.png) and a link [text](url.com)"

    # Act
    links = extract_markdown_links(text)

    # Assert
    assert len(links) == 1
    assert links[0].text == "text"
    assert links[0].url == "url.com"


@pytest.mark.ai
def test_extract_markdown_links__returns_empty_list__for_text_without_links() -> None:
    """
    Purpose: Verify extract_markdown_links returns empty list for text without links.
    Why this matters: Ensures graceful handling of text without markdown links.
    Setup summary: Provide plain text and verify empty result.
    """
    # Arrange
    text = "This is plain text without any links."

    # Act
    links = extract_markdown_links(text)

    # Assert
    assert links == []


@pytest.mark.ai
def test_create_content_references_from_links__creates_references__with_sequence_numbers() -> (
    None
):
    """
    Purpose: Verify create_content_references_from_links creates proper ContentReference objects.
    Why this matters: ContentReference objects are used for citation management.
    Setup summary: Provide markdown links and verify ContentReference creation.
    """
    # Arrange
    links = [
        MarkdownLink(
            text="OpenAI",
            url="https://openai.com",
            full_match="[OpenAI](https://openai.com)",
        ),
        MarkdownLink(
            text="Google",
            url="https://google.com",
            full_match="[Google](https://google.com)",
        ),
    ]
    message_id = "test-message"

    # Act
    references = create_content_references_from_links(links, message_id)

    # Assert
    assert len(references) == 2
    assert references[0].sequence_number == 1
    assert references[0].name == "OpenAI"
    assert references[0].url == "https://openai.com"
    assert references[0].message_id == message_id
    assert references[1].sequence_number == 2
    assert references[1].name == "Google"


@pytest.mark.ai
def test_create_content_references_from_links__skips_duplicate_urls__and_maintains_sequence() -> (
    None
):
    """
    Purpose: Verify create_content_references_from_links skips duplicate URLs.
    Why this matters: Prevents duplicate citations for the same source.
    Setup summary: Provide links with duplicate URLs and verify deduplication.
    """
    # Arrange
    links = [
        MarkdownLink(
            text="OpenAI",
            url="https://openai.com",
            full_match="[OpenAI](https://openai.com)",
        ),
        MarkdownLink(
            text="OpenAI Site",
            url="https://openai.com",
            full_match="[OpenAI Site](https://openai.com)",
        ),
        MarkdownLink(
            text="Google",
            url="https://google.com",
            full_match="[Google](https://google.com)",
        ),
    ]

    # Act
    references = create_content_references_from_links(links)

    # Assert
    assert len(references) == 2
    assert references[0].sequence_number == 1
    assert references[0].url == "https://openai.com"
    assert references[1].sequence_number == 2
    assert references[1].url == "https://google.com"


@pytest.mark.ai
def test_create_content_references_and_chunks_from_links__creates_both_types__from_same_data() -> (
    None
):
    """
    Purpose: Verify create_content_references_and_chunks_from_links creates both references and chunks.
    Why this matters: Unified function ensures consistency between references and chunks.
    Setup summary: Provide links and verify both ContentReference and ContentChunk creation.
    """
    # Arrange
    links = [
        MarkdownLink(
            text="OpenAI",
            url="https://openai.com",
            full_match="[OpenAI](https://openai.com)",
        ),
    ]
    tool_call_id = "test-tool"
    message_id = "test-message"

    # Act
    references, chunks = create_content_references_and_chunks_from_links(
        links, tool_call_id, message_id
    )

    # Assert
    assert len(references) == 1
    assert len(chunks) == 1
    assert references[0].name == "OpenAI"
    assert references[0].url == "https://openai.com"
    assert chunks[0].text == "OpenAI"
    assert chunks[0].url == "https://openai.com"
    assert chunks[0].id == f"deep-research-{tool_call_id}-https://openai.com"


@pytest.mark.ai
def test_replace_links_with_superscript_references__replaces_links__with_superscript_numbers() -> (
    None
):
    """
    Purpose: Verify replace_links_with_superscript_references converts markdown links to superscripts.
    Why this matters: Superscript references provide clean citation format in final reports.
    Setup summary: Provide text with links and verify superscript replacement.
    """
    # Arrange
    text = "Check [OpenAI](https://openai.com) and [Google](https://google.com)"
    links = [
        MarkdownLink(
            text="OpenAI",
            url="https://openai.com",
            full_match="[OpenAI](https://openai.com)",
        ),
        MarkdownLink(
            text="Google",
            url="https://google.com",
            full_match="[Google](https://google.com)",
        ),
    ]

    # Act
    result = replace_links_with_superscript_references(text, links)

    # Assert
    assert "<sup>1</sup>" in result
    assert "<sup>2</sup>" in result
    assert "[OpenAI](https://openai.com)" not in result
    assert "[Google](https://google.com)" not in result


@pytest.mark.ai
def test_replace_links_with_superscript_references__handles_duplicate_urls__with_same_number() -> (
    None
):
    """
    Purpose: Verify replace_links_with_superscript_references handles duplicate URLs consistently.
    Why this matters: Duplicate URLs should get the same reference number.
    Setup summary: Provide links with duplicate URLs and verify consistent numbering.
    """
    # Arrange
    text = "Check [OpenAI](https://openai.com) and [OpenAI Site](https://openai.com)"
    links = [
        MarkdownLink(
            text="OpenAI",
            url="https://openai.com",
            full_match="[OpenAI](https://openai.com)",
        ),
        MarkdownLink(
            text="OpenAI Site",
            url="https://openai.com",
            full_match="[OpenAI Site](https://openai.com)",
        ),
    ]

    # Act
    result = replace_links_with_superscript_references(text, links)

    # Assert
    assert result.count("<sup>1</sup>") == 2
    assert "<sup>2</sup>" not in result


@pytest.mark.ai
def test_postprocess_research_result_complete__processes_text__with_links() -> None:
    """
    Purpose: Verify postprocess_research_result_complete processes research results correctly.
    Why this matters: Complete pipeline for processing research results with citations.
    Setup summary: Provide research text with links and verify processing.
    """
    # Arrange
    research_result = "AI research from [OpenAI](https://openai.com) shows progress."
    message_id = "test-message"

    # Act
    processed_text, references = postprocess_research_result_complete(
        research_result, message_id
    )

    # Assert
    assert "<sup>1</sup>" in processed_text
    assert len(references) == 1
    assert references[0].name == "OpenAI"
    assert references[0].url == "https://openai.com"


@pytest.mark.ai
def test_postprocess_research_result_complete__returns_original__for_empty_text() -> (
    None
):
    """
    Purpose: Verify postprocess_research_result_complete handles empty text gracefully.
    Why this matters: Ensures robust handling of edge cases.
    Setup summary: Provide empty text and verify original is returned.
    """
    # Arrange
    research_result = ""

    # Act
    processed_text, references = postprocess_research_result_complete(research_result)

    # Assert
    assert processed_text == ""
    assert references == []


@pytest.mark.ai
def test_postprocess_research_result_with_chunks__creates_chunks__alongside_references() -> (
    None
):
    """
    Purpose: Verify postprocess_research_result_with_chunks creates both references and chunks.
    Why this matters: Provides complete content processing for research results.
    Setup summary: Provide research text and verify both references and chunks are created.
    """
    # Arrange
    research_result = "Research from [OpenAI](https://openai.com) is important."
    tool_call_id = "test-tool"
    message_id = "test-message"

    # Act
    processed_text, references, chunks = postprocess_research_result_with_chunks(
        research_result, tool_call_id, message_id
    )

    # Assert
    assert "<sup>1</sup>" in processed_text
    assert len(references) == 1
    assert len(chunks) == 1
    assert references[0].name == "OpenAI"
    assert chunks[0].text == "OpenAI"


@pytest.mark.ai
def test_extract_sup_citations__finds_superscript_numbers__in_text() -> None:
    """
    Purpose: Verify extract_sup_citations finds all superscript citation numbers.
    Why this matters: Used for validating citations against registry.
    Setup summary: Provide text with superscript citations and verify extraction.
    """
    # Arrange
    text = "Research shows<sup>1</sup> that AI<sup>2</sup> is advancing<sup>1</sup>."

    # Act
    citations = extract_sup_citations(text)

    # Assert
    assert citations == {1, 2}


@pytest.mark.ai
def test_extract_sup_citations__returns_empty_set__for_text_without_citations() -> None:
    """
    Purpose: Verify extract_sup_citations returns empty set for text without citations.
    Why this matters: Ensures graceful handling of text without superscript citations.
    Setup summary: Provide plain text and verify empty result.
    """
    # Arrange
    text = "This is plain text without any citations."

    # Act
    citations = extract_sup_citations(text)

    # Assert
    assert citations == set()


@pytest.mark.ai
def test_validate_and_map_citations__validates_citations__against_registry() -> None:
    """
    Purpose: Verify validate_and_map_citations validates citations against registry.
    Why this matters: Ensures all citations in report have valid sources.
    Setup summary: Provide report with citations and registry, verify validation.
    """
    # Arrange
    report = "Research shows<sup>1</sup> progress<sup>2</sup>."
    citation_registry = {
        "source1": CitationMetadata(
            number=1, name="Source 1", url="url1", type="web", source_id="source1"
        ),
        "source2": CitationMetadata(
            number=2, name="Source 2", url="url2", type="web", source_id="source2"
        ),
    }

    # Act
    processed_report, references = validate_and_map_citations(report, citation_registry)

    # Assert
    assert processed_report == report  # No invalid citations to remove
    assert len(references) == 2
    assert references[0].name == "Source 1"
    assert references[0].sequence_number == 1
    assert references[1].name == "Source 2"
    assert references[1].sequence_number == 2


@pytest.mark.ai
def test_validate_and_map_citations__removes_invalid_citations__from_report() -> None:
    """
    Purpose: Verify validate_and_map_citations removes invalid citations.
    Why this matters: Prevents broken citations from appearing in final report.
    Setup summary: Provide report with invalid citations and verify removal.
    """
    # Arrange
    report = "Research shows<sup>1</sup> progress<sup>99</sup>."
    citation_registry = {
        "source1": CitationMetadata(
            number=1, name="Source 1", url="url1", type="web", source_id="source1"
        ),
    }

    # Act
    processed_report, references = validate_and_map_citations(report, citation_registry)

    # Assert
    assert "<sup>1</sup>" in processed_report
    assert "<sup>99</sup>" not in processed_report
    assert len(references) == 1
    assert references[0].sequence_number == 1


@pytest.mark.ai
def test_remap_and_append_docx_references__remaps_sup_to_markdown_links__and_appends_sources() -> (
    None
):
    """
    Purpose: Verify _remap_and_append_docx_references converts sup refs to markdown and adds Sources.
    Why this matters: DOCX export requires markdown links and a Sources section for Pandoc conversion.
    Setup summary: Report with <sup>N</sup> refs, references dict, verify remapping and Sources format.
    """
    # Arrange
    report = "Text<sup>1</sup> and<sup>2</sup>."
    references = {
        1: ContentReference(
            name="OpenAI",
            url="https://openai.com",
            sequence_number=1,
            source="web",
            source_id="1",
        ),
        2: ContentReference(
            name="Google",
            url="https://google.com",
            sequence_number=2,
            source="web",
            source_id="2",
        ),
    }

    # Act
    result = _remap_and_append_docx_references(report, references)

    # Assert
    assert "[[1]](https://openai.com)" in result
    assert "[[2]](https://google.com)" in result
    assert "<sup>1</sup>" not in result
    assert "<sup>2</sup>" not in result
    assert "# Sources" in result
    assert "[1] [OpenAI](https://openai.com)" in result
    assert "[2] [Google](https://google.com)" in result


@pytest.mark.ai
def test_remap_and_append_docx_references__preserves_citation_number_gaps__in_sources() -> (
    None
):
    """
    Purpose: Verify Sources section uses original citation numbers (1, 3, 5) not sequential (1, 2, 3).
    Why this matters: validate_and_map_citations may remove invalid refs, leaving gaps; in-text [[3]] must match Sources.
    Setup summary: Report with refs 1, 3, 5; verify Sources shows [1], [3], [5] format.
    """
    # Arrange
    report = "Text<sup>1</sup><sup>3</sup><sup>5</sup>."
    references = {
        1: ContentReference(
            name="First",
            url="https://a.com",
            sequence_number=1,
            source="web",
            source_id="1",
        ),
        3: ContentReference(
            name="Third",
            url="unique://content/x",
            sequence_number=3,
            source="report",
            source_id="x",
        ),
        5: ContentReference(
            name="Fifth",
            url="https://e.com",
            sequence_number=5,
            source="web",
            source_id="5",
        ),
    }

    # Act
    result = _remap_and_append_docx_references(report, references)

    # Assert - Sources uses original numbers [1], [3], [5], not sequential [1], [2], [3]
    assert "[1] [First](https://a.com)" in result
    assert "[3] Third" in result
    assert "[5] [Fifth](https://e.com)" in result
    assert "[2]" not in result


@pytest.mark.ai
def test_remap_and_append_docx_references__non_https_urls__rendered_without_link() -> (
    None
):
    """
    Purpose: Verify non-https refs (e.g. unique://) use plain [N] in text and [N] Name in Sources.
    Why this matters: Internal content refs don't have external URLs.
    Setup summary: Ref with unique:// URL; verify [N] and no markdown link in Sources.
    """
    # Arrange
    report = "See<sup>1</sup>."
    references = {
        1: ContentReference(
            name="Internal Report",
            url="unique://content/abc",
            sequence_number=1,
            source="report",
            source_id="abc",
        ),
    }

    # Act
    result = _remap_and_append_docx_references(report, references)

    # Assert
    assert "[1]" in result
    assert "unique://" not in result
    assert "[1] Internal Report" in result


@pytest.mark.ai
def test_remap_and_append_docx_references__removes_invalid_refs__from_report() -> None:
    """
    Purpose: Verify ref numbers not in references dict are removed from report.
    Why this matters: Stale or invalid citations should not appear in DOCX.
    Setup summary: Report with refs 1 and 99; only ref 1 in registry; verify 99 removed.
    """
    # Arrange
    report = "Text<sup>1</sup> and<sup>99</sup>."
    references = {
        1: ContentReference(
            name="Valid",
            url="https://v.com",
            sequence_number=1,
            source="web",
            source_id="1",
        ),
    }

    # Act
    result = _remap_and_append_docx_references(report, references)

    # Assert
    assert "<sup>1</sup>" not in result
    assert "<sup>99</sup>" not in result
    assert "[[1]](https://v.com)" in result
    assert "# Sources" in result
    assert "[99]" not in result  # Invalid ref not in Sources


@pytest.mark.ai
def test_remap_and_append_docx_references__sources_have_hard_line_breaks() -> None:
    """
    Purpose: Verify each Sources entry ends with trailing double-space for Pandoc hard line break.
    Why this matters: Ensures each source appears on its own line in DOCX without extra paragraph spacing.
    Setup summary: Multiple refs; verify Sources lines end with two spaces.
    """
    # Arrange
    report = "Text<sup>1</sup><sup>2</sup>."
    references = {
        1: ContentReference(
            name="A",
            url="https://a.com",
            sequence_number=1,
            source="web",
            source_id="1",
        ),
        2: ContentReference(
            name="B",
            url="https://b.com",
            sequence_number=2,
            source="web",
            source_id="2",
        ),
    }

    # Act
    result = _remap_and_append_docx_references(report, references)

    # Assert - each Sources line ends with two spaces for Pandoc hard line break
    assert "[1] [A](https://a.com)  " in result
    assert "[2] [B](https://b.com)  " in result


@pytest.mark.ai
def test_remap_and_append_docx_references__returns_unchanged__when_no_refs() -> None:
    """
    Purpose: Verify report is returned unchanged when it has no sup references.
    Why this matters: Edge case for reports without citations.
    Setup summary: Plain text report; verify no Sources section added.
    """
    # Arrange
    report = "No citations here."
    references: dict[int, ContentReference] = {}

    # Act
    result = _remap_and_append_docx_references(report, references)

    # Assert
    assert result == report
    assert "# Sources" not in result


@pytest.mark.ai
def test_remove_horizontal_rules__removes_dashes_asterisks_underscores() -> None:
    """
    Purpose: Verify _remove_horizontal_rules removes ---, ***, ___ horizontal rules.
    Why this matters: DOCX export may strip markdown dividers per config.
    Setup summary: Text with various horizontal rules; verify they are removed.
    """
    # Arrange
    text = "Section 1\n---\nSection 2\n***\nSection 3\n___\nSection 4"

    # Act
    result = _remove_horizontal_rules(text)

    # Assert
    assert "---" not in result
    assert "***" not in result
    assert "___" not in result
    assert "Section 1" in result
    assert "Section 2" in result
    assert "Section 3" in result
    assert "Section 4" in result


@pytest.mark.ai
def test_remove_horizontal_rules__preserves_content__without_rules() -> None:
    """
    Purpose: Verify _remove_horizontal_rules leaves text unchanged when no rules present.
    Why this matters: Idempotent for normal content.
    Setup summary: Plain text; verify unchanged.
    """
    # Arrange
    text = "Just some normal text with - dashes and * asterisks."

    # Act
    result = _remove_horizontal_rules(text)

    # Assert
    assert result == text
