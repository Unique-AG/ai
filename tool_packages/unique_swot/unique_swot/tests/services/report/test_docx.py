"""Tests for DOCX conversion functionality."""

from unittest.mock import Mock

import pytest

from unique_swot.services.report.docx import convert_markdown_to_docx


class TestConvertMarkdownToDocx:
    """Test cases for convert_markdown_to_docx function."""

    @pytest.fixture
    def mock_docx_generator(self):
        """Create a mock DOCX generator service."""
        service = Mock()
        service.parse_markdown_to_list_content_fields.return_value = [
            {"type": "heading", "content": "Test Report"},
            {"type": "paragraph", "content": "Test content"},
        ]
        service.generate_from_template.return_value = b"fake docx bytes content"
        return service

    def test_convert_markdown_to_docx_success(self, mock_docx_generator):
        """Test successful markdown to DOCX conversion."""
        markdown_content = "# Test Report\n\nTest content paragraph."
        fields = {"title": "SWOT Analysis", "date": "2024-01-01"}

        result = convert_markdown_to_docx(
            markdown_content=markdown_content,
            docx_generator_service=mock_docx_generator,
            fields=fields,
        )

        # Verify parse was called with markdown
        mock_docx_generator.parse_markdown_to_list_content_fields.assert_called_once_with(
            markdown_content
        )

        # Verify generate was called with parsed fields and template fields
        mock_docx_generator.generate_from_template.assert_called_once()
        call_args = mock_docx_generator.generate_from_template.call_args
        assert call_args[0][1] == fields

        # Verify return value
        assert result == b"fake docx bytes content"
        assert isinstance(result, bytes)

    def test_convert_empty_markdown(self, mock_docx_generator):
        """Test converting empty markdown."""
        markdown_content = ""
        fields = {}

        result = convert_markdown_to_docx(
            markdown_content=markdown_content,
            docx_generator_service=mock_docx_generator,
            fields=fields,
        )

        # Should still call both methods
        mock_docx_generator.parse_markdown_to_list_content_fields.assert_called_once()
        mock_docx_generator.generate_from_template.assert_called_once()

        assert result is not None

    def test_convert_markdown_with_complex_formatting(self, mock_docx_generator):
        """Test converting markdown with various formatting."""
        markdown_content = """
# Main Title

## Section 1

This is **bold** and *italic* text.

- Bullet point 1
- Bullet point 2

## Section 2

> Quote block

1. Numbered item
2. Another item

[Link text](http://example.com)
"""
        fields = {"title": "Complex Report", "author": "Test User"}

        result = convert_markdown_to_docx(
            markdown_content=markdown_content,
            docx_generator_service=mock_docx_generator,
            fields=fields,
        )

        # Verify parsing was called
        mock_docx_generator.parse_markdown_to_list_content_fields.assert_called_once_with(
            markdown_content
        )

        # Verify result
        assert result is not None
        assert isinstance(result, bytes)

    def test_convert_markdown_with_citations(self, mock_docx_generator):
        """Test converting markdown with citation superscripts."""
        markdown_content = """
# SWOT Analysis

## Strengths
- Strong brand<sup>1</sup>
- Market leader<sup>2</sup>

## References
1. Annual Report 2023: page 15
2. Market Research: page 7
"""
        fields = {}

        result = convert_markdown_to_docx(
            markdown_content=markdown_content,
            docx_generator_service=mock_docx_generator,
            fields=fields,
        )

        # Verify successful conversion
        assert result is not None
        mock_docx_generator.parse_markdown_to_list_content_fields.assert_called_once()

    def test_convert_returns_none_when_generation_fails(self, mock_docx_generator):
        """Test that None is returned when generation fails."""
        mock_docx_generator.generate_from_template.return_value = None

        markdown_content = "# Test"
        fields = {}

        result = convert_markdown_to_docx(
            markdown_content=markdown_content,
            docx_generator_service=mock_docx_generator,
            fields=fields,
        )

        assert result is None

    def test_convert_with_no_fields(self, mock_docx_generator):
        """Test conversion without template fields."""
        markdown_content = "# Simple Report\n\nContent here."
        fields = {}

        result = convert_markdown_to_docx(
            markdown_content=markdown_content,
            docx_generator_service=mock_docx_generator,
            fields=fields,
        )

        # Should still work with empty fields
        mock_docx_generator.generate_from_template.assert_called_once()
        call_args = mock_docx_generator.generate_from_template.call_args
        assert call_args[0][1] == {}

        assert result is not None

    def test_convert_with_multiple_fields(self, mock_docx_generator):
        """Test conversion with multiple template fields."""
        markdown_content = "# Report"
        fields = {
            "title": "SWOT Analysis Report",
            "date": "2024-12-31",
            "author": "AI Assistant",
            "company": "Acme Corp",
            "version": "1.0",
        }

        result = convert_markdown_to_docx(
            markdown_content=markdown_content,
            docx_generator_service=mock_docx_generator,
            fields=fields,
        )

        # Verify all fields passed to generator
        call_args = mock_docx_generator.generate_from_template.call_args
        passed_fields = call_args[0][1]
        assert passed_fields == fields
        assert len(passed_fields) == 5

        assert result is not None

    def test_convert_markdown_with_special_characters(self, mock_docx_generator):
        """Test converting markdown with special characters."""
        markdown_content = """
# Report: Q1 & Q2 Analysis

Revenue increased by 50% & profit > $1M.

**Note**: Data is "preliminary"
"""
        fields = {"title": "Q1&Q2 Report"}

        result = convert_markdown_to_docx(
            markdown_content=markdown_content,
            docx_generator_service=mock_docx_generator,
            fields=fields,
        )

        # Should handle special characters
        mock_docx_generator.parse_markdown_to_list_content_fields.assert_called_once()
        assert result is not None

    def test_convert_large_markdown_document(self, mock_docx_generator):
        """Test converting a large markdown document."""
        # Create a large markdown document
        sections = []
        for i in range(10):
            sections.append(f"## Section {i}\n\n")
            sections.append("Lorem ipsum dolor sit amet. " * 50)
            sections.append("\n\n")

        markdown_content = "# Large Report\n\n" + "".join(sections)
        fields = {"title": "Large Report"}

        result = convert_markdown_to_docx(
            markdown_content=markdown_content,
            docx_generator_service=mock_docx_generator,
            fields=fields,
        )

        # Should handle large documents
        assert result is not None
        mock_docx_generator.parse_markdown_to_list_content_fields.assert_called_once()

    def test_convert_preserves_markdown_structure(self, mock_docx_generator):
        """Test that markdown structure is preserved in parsing."""
        markdown_content = """
# Title
## Subtitle
### Sub-subtitle

Paragraph text.

- Item 1
  - Nested item
- Item 2
"""
        fields = {}

        convert_markdown_to_docx(
            markdown_content=markdown_content,
            docx_generator_service=mock_docx_generator,
            fields=fields,
        )

        # Verify the exact markdown was passed to parser
        call_args = mock_docx_generator.parse_markdown_to_list_content_fields.call_args
        assert call_args[0][0] == markdown_content
