"""Tests for DOCX conversion utilities."""

from unittest.mock import Mock

from unique_swot.services.report.docx import (
    add_citation_footer,
    convert_markdown_to_docx,
)


def test_add_citation_footer_with_citations():
    """Test adding citation footer with multiple citations."""
    markdown = "# Report\n\nContent here."
    citations = ["[1] Document A", "[2] Document B", "[3] Document C"]

    result = add_citation_footer(markdown, citations)

    assert "# Report" in result
    assert "Content here." in result
    assert "[1] Document A" in result
    assert "[2] Document B" in result
    assert "[3] Document C" in result


def test_add_citation_footer_empty_citations():
    """Test adding citation footer with no citations."""
    markdown = "# Report\n\nContent here."
    citations = []

    result = add_citation_footer(markdown, citations)

    # Should still return the original markdown
    assert "# Report" in result
    assert "Content here." in result


def test_add_citation_footer_preserves_markdown():
    """Test that citation footer preserves original markdown formatting."""
    markdown = "# Title\n\n## Subtitle\n\n- Bullet 1\n- Bullet 2\n\n**Bold text**"
    citations = ["[1] Source"]

    result = add_citation_footer(markdown, citations)

    # Original formatting should be preserved
    assert "# Title" in result
    assert "## Subtitle" in result
    assert "- Bullet 1" in result
    assert "- Bullet 2" in result
    assert "**Bold text**" in result
    assert "[1] Source" in result


def test_convert_markdown_to_docx_success():
    """Test successful markdown to DOCX conversion."""
    markdown = "# Test Report\n\nContent"
    fields = {"title": "SWOT Analysis", "date": "2024-01-01"}

    docx_generator = Mock()
    docx_generator.parse_markdown_to_list_content_fields.return_value = [
        {"type": "heading", "content": "Test Report"},
        {"type": "paragraph", "content": "Content"},
    ]
    docx_generator.generate_from_template.return_value = b"fake docx bytes"

    result = convert_markdown_to_docx(markdown, docx_generator, fields)

    assert result == b"fake docx bytes"
    docx_generator.parse_markdown_to_list_content_fields.assert_called_once_with(
        markdown
    )
    docx_generator.generate_from_template.assert_called_once()


def test_convert_markdown_to_docx_with_complex_markdown():
    """Test conversion with complex markdown elements."""
    markdown = """
# Main Title

## Section 1

This is a paragraph with **bold** and *italic* text.

- Bullet point 1
- Bullet point 2

## Section 2

1. Numbered item 1
2. Numbered item 2

> Quote block

[Link text](https://example.com)
"""
    fields = {"title": "Report", "date": "2024-01-01"}

    docx_generator = Mock()
    docx_generator.parse_markdown_to_list_content_fields.return_value = [
        {"type": "heading", "level": 1, "content": "Main Title"},
        {"type": "heading", "level": 2, "content": "Section 1"},
        {"type": "paragraph", "content": "This is a paragraph..."},
    ]
    docx_generator.generate_from_template.return_value = b"docx content"

    result = convert_markdown_to_docx(markdown, docx_generator, fields)

    assert result == b"docx content"
    # Verify markdown was parsed
    docx_generator.parse_markdown_to_list_content_fields.assert_called_once()


def test_convert_markdown_to_docx_passes_fields():
    """Test that template fields are passed correctly."""
    markdown = "# Report"
    fields = {
        "title": "ACME Corp SWOT Analysis",
        "date": "2024-01-15",
        "author": "Analysis Team",
    }

    docx_generator = Mock()
    docx_generator.parse_markdown_to_list_content_fields.return_value = []
    docx_generator.generate_from_template.return_value = b"docx"

    convert_markdown_to_docx(markdown, docx_generator, fields)

    # Verify fields were passed to generate_from_template
    call_args = docx_generator.generate_from_template.call_args
    assert call_args[0][1] == fields


def test_convert_markdown_to_docx_returns_none_on_failure():
    """Test that conversion returns None on failure."""
    markdown = "# Report"
    fields = {"title": "Report"}

    docx_generator = Mock()
    docx_generator.parse_markdown_to_list_content_fields.return_value = []
    docx_generator.generate_from_template.return_value = None  # Failure

    result = convert_markdown_to_docx(markdown, docx_generator, fields)

    assert result is None


def test_convert_markdown_to_docx_empty_markdown():
    """Test conversion with empty markdown."""
    markdown = ""
    fields = {"title": "Report"}

    docx_generator = Mock()
    docx_generator.parse_markdown_to_list_content_fields.return_value = []
    docx_generator.generate_from_template.return_value = b"empty docx"

    result = convert_markdown_to_docx(markdown, docx_generator, fields)

    assert result == b"empty docx"


def test_add_citation_footer_with_special_characters():
    """Test citation footer with special characters in citations."""
    markdown = "# Report"
    citations = [
        "[1] Document with & ampersand",
        "[2] Document with < and >",
        '[3] Document with "quotes"',
    ]

    result = add_citation_footer(markdown, citations)

    # Special characters should be preserved
    assert "& ampersand" in result
    assert "< and >" in result
    assert '"quotes"' in result
