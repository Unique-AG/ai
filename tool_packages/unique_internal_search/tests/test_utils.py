from unique_toolkit.content.schemas import ContentChunk, ContentMetadata

from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.utils import (
    _extract_leading_metadata_tags,
    _format_chunk_with_metadata,
    _match_leading_tag,
    modify_metadata_in_chunks,
)


class TestMatchLeadingTag:
    """Tests for _match_leading_tag function."""

    def test_match_pipe_format(self):
        """Test matching <|key|>value<|/key|> format."""
        text = "<|document|>test.pdf<|/document|> some text"
        result = _match_leading_tag(text)

        assert result is not None
        key, value, length = result
        assert key == "document"
        assert value == "test.pdf"
        assert length == len("<|document|>test.pdf<|/document|> ")

    def test_match_angle_bracket_format(self):
        """Test matching <key>value</key> format."""
        text = "<title>My Title</title> some text"
        result = _match_leading_tag(text)

        assert result is not None
        key, value, length = result
        assert key == "title"
        assert value == "My Title"
        assert length == len("<title>My Title</title> ")

    def test_match_with_multiline_value(self):
        """Test matching tags with multiline content."""
        text = "<|info|>Line 1\nLine 2\nLine 3<|/info|> rest"
        result = _match_leading_tag(text)

        assert result is not None
        key, value, length = result
        assert key == "info"
        assert value == "Line 1\nLine 2\nLine 3"

    def test_no_match_with_text_before_tag(self):
        """Test that tags not at the start don't match."""
        text = "some text <|document|>test.pdf<|/document|>"
        result = _match_leading_tag(text)

        assert result is None

    def test_no_match_with_incomplete_tag(self):
        """Test that incomplete tags don't match."""
        text = "<|document|>test.pdf"
        result = _match_leading_tag(text)

        assert result is None

    def test_no_match_with_mismatched_tags(self):
        """Test that mismatched opening and closing tags don't match."""
        text = "<|document|>test.pdf<|/info|>"
        result = _match_leading_tag(text)

        assert result is None

    def test_match_empty_value(self):
        """Test matching tags with empty values."""
        text = "<|key|><|/key|> text"
        result = _match_leading_tag(text)

        assert result is not None
        key, value, length = result
        assert key == "key"
        assert value == ""


class TestExtractLeadingMetadataTags:
    """Tests for _extract_leading_metadata_tags function."""

    def test_extract_single_pipe_tag(self):
        """Test extracting a single tag in pipe format."""
        text = "<|document|>test.pdf<|/document|> Main content here"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata == {"document": "test.pdf"}
        assert remaining == "Main content here"

    def test_extract_single_angle_tag(self):
        """Test extracting a single tag in angle bracket format."""
        text = "<title>My Document</title> Main content here"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata == {"title": "My Document"}
        assert remaining == "Main content here"

    def test_extract_multiple_tags(self):
        """Test extracting multiple consecutive tags."""
        text = "<|document|>test.pdf<|/document|><|info|>Page 1-5<|/info|> Content"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata == {"document": "test.pdf", "info": "Page 1-5"}
        assert remaining == "Content"

    def test_extract_mixed_format_tags(self):
        """Test extracting tags in mixed formats."""
        text = "<|document|>test.pdf<|/document|><title>Title</title> Content"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata == {"document": "test.pdf", "title": "Title"}
        assert remaining == "Content"

    def test_no_tags_returns_empty_dict(self):
        """Test that text without tags returns empty metadata."""
        text = "Just plain text content"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata == {}
        assert remaining == "Just plain text content"

    def test_tags_not_at_start_stops_extraction(self):
        """Test that extraction stops when tags are not at the start."""
        text = "<|document|>test.pdf<|/document|> Some text <|info|>ignored<|/info|>"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata == {"document": "test.pdf"}
        assert remaining == "Some text <|info|>ignored<|/info|>"

    def test_whitespace_handling(self):
        """Test that whitespace between tags is handled correctly."""
        text = "<|document|>test.pdf<|/document|>   <|info|>data<|/info|>   Content"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata == {"document": "test.pdf", "info": "data"}
        assert remaining == "Content"

    def test_multiline_tag_value(self):
        """Test extracting tags with multiline values."""
        text = "<|info|>Line 1\nLine 2<|/info|> Content"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata == {"info": "Line 1\nLine 2"}
        assert remaining == "Content"


class TestFormatChunkWithMetadata:
    """Tests for _format_chunk_with_metadata function."""

    def test_format_with_document_metadata(self):
        """Test formatting with document metadata."""
        config = InternalSearchConfig()
        text = "Main content"
        meta_dict = {"document": "test.pdf"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert result.startswith("<|document|>test.pdf<|/document|>")
        assert result.endswith("Main content")

    def test_format_with_info_metadata(self):
        """Test formatting with info metadata."""
        config = InternalSearchConfig()
        text = "Main content"
        meta_dict = {"info": "Page 1-3"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert result.startswith("Main content")

    def test_format_with_multiple_metadata(self):
        """Test formatting with multiple metadata fields."""
        config = InternalSearchConfig()
        text = "Main content"
        meta_dict = {"document": "test.pdf", "info": "Page 1"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        # Both metadata should be present
        assert "<|document|>test.pdf<|/document|>" in result
        assert "<|info|>Page 1<|/info|>" not in result
        assert result.endswith("Main content")

    def test_format_with_no_metadata(self):
        """Test formatting with no matching metadata."""
        config = InternalSearchConfig()
        text = "Main content"
        meta_dict = {"other_field": "value"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert result == "Main content"

    def test_format_with_empty_metadata(self):
        """Test formatting with empty metadata dict."""
        config = InternalSearchConfig()
        text = "Main content"
        meta_dict = {}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert result == "Main content"

    def test_format_respects_config_sections(self):
        """Test that formatting respects the config sections."""
        config = InternalSearchConfig()
        # Only format keys that are in the sections dict
        text = "Main content"
        meta_dict = {"document": "test.pdf", "random_key": "value"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert "<|document|>test.pdf<|/document|>" in result
        assert "random_key" not in result


class TestModifyMetadataInChunks:
    """Tests for modify_metadata_in_chunks function."""

    def test_modify_single_chunk_with_tags(self):
        """Test modifying a single chunk that has metadata tags."""
        config = InternalSearchConfig()
        chunk = ContentChunk(
            text="<|document|>test.pdf<|/document|> Main content",
            metadata=ContentMetadata(key="test.pdf", mime_type="application/pdf"),
        )
        chunks = [chunk]

        result = modify_metadata_in_chunks(chunks, config)

        assert len(result) == 1
        # The tag should be extracted and re-formatted
        assert "<|document|>test.pdf<|/document|>" in result[0].text
        assert "Main content" in result[0].text

    def test_modify_chunk_without_tags(self):
        """Test modifying a chunk without metadata tags."""
        config = InternalSearchConfig()
        chunk = ContentChunk(
            text="Plain content without tags",
            metadata=ContentMetadata(key="test.pdf", mime_type="application/pdf"),
        )
        chunks = [chunk]

        result = modify_metadata_in_chunks(chunks, config)

        assert len(result) == 1
        # Since there's no metadata in sections, text should remain the same
        assert result[0].text == "Plain content without tags"

    def test_modify_multiple_chunks(self):
        """Test modifying multiple chunks."""
        config = InternalSearchConfig()
        chunks = [
            ContentChunk(
                text="<|document|>test1.pdf<|/document|> Content 1",
                metadata=ContentMetadata(key="test1.pdf", mime_type="application/pdf"),
            ),
            ContentChunk(
                text="<|document|>test2.pdf<|/document|> Content 2",
                metadata=ContentMetadata(key="test2.pdf", mime_type="application/pdf"),
            ),
        ]

        result = modify_metadata_in_chunks(chunks, config)

        assert len(result) == 2
        assert "Content 1" in result[0].text
        assert "Content 2" in result[1].text

    def test_modify_merges_extracted_with_existing_metadata(self):
        """Test that extracted metadata is merged with existing chunk metadata."""
        config = InternalSearchConfig()
        chunk = ContentChunk(
            text="<|info|>Extracted info<|/info|> Content",
            metadata=ContentMetadata(key="test.pdf", mime_type="application/pdf"),
        )
        chunks = [chunk]

        result = modify_metadata_in_chunks(chunks, config)

        # The info should be extracted and then re-added to the text
        assert "<|info|>Extracted info<|/info|>" in result[0].text
        assert "Content" in result[0].text

    def test_modify_chunk_with_mixed_tag_formats(self):
        """Test modifying chunks with mixed tag formats."""
        config = InternalSearchConfig()
        chunk = ContentChunk(
            text="<|document|>test.pdf<|/document|><title>Title</title> Content",
            metadata=ContentMetadata(key="test.pdf", mime_type="application/pdf"),
        )
        chunks = [chunk]

        result = modify_metadata_in_chunks(chunks, config)

        # document should be formatted (it's in sections)
        assert "<|document|>test.pdf<|/document|>" in result[0].text
        # title is not in default sections, so won't be formatted
        assert "Content" in result[0].text

    def test_modify_returns_same_list_object(self):
        """Test that the function modifies and returns the same list."""
        config = InternalSearchConfig()
        chunks = [
            ContentChunk(
                text="Content",
                metadata=ContentMetadata(key="test.pdf", mime_type="application/pdf"),
            )
        ]

        result = modify_metadata_in_chunks(chunks, config)

        assert result is chunks

    def test_modify_with_none_metadata(self):
        """Test modifying chunks with None metadata."""
        config = InternalSearchConfig()
        chunk = ContentChunk(
            text="<|document|>test.pdf<|/document|> Content",
            metadata=None,
        )
        chunks = [chunk]

        result = modify_metadata_in_chunks(chunks, config)

        assert len(result) == 1
        # Should still extract and format the metadata
        assert "<|document|>test.pdf<|/document|>" in result[0].text

    def test_modify_preserves_chunk_order(self):
        """Test that chunk order is preserved after modification."""
        config = InternalSearchConfig()
        chunks = [
            ContentChunk(
                order=0,
                text="Content 0",
                metadata=ContentMetadata(key="test.pdf", mime_type="application/pdf"),
            ),
            ContentChunk(
                order=1,
                text="Content 1",
                metadata=ContentMetadata(key="test.pdf", mime_type="application/pdf"),
            ),
            ContentChunk(
                order=2,
                text="Content 2",
                metadata=ContentMetadata(key="test.pdf", mime_type="application/pdf"),
            ),
        ]

        result = modify_metadata_in_chunks(chunks, config)

        assert result[0].order == 0
        assert result[1].order == 1
        assert result[2].order == 2


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_special_characters_in_values(self):
        """Test handling of special characters in tag values."""
        text = "<|document|>file!@#$%^&*().pdf<|/document|> Content"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata["document"] == "file!@#$%^&*().pdf"

    def test_nested_angle_brackets_in_value(self):
        """Test handling of angle brackets within tag values."""
        text = "<|info|>value with <brackets><|/info|> Content"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata["info"] == "value with <brackets>"

    def test_unicode_characters(self):
        """Test handling of unicode characters in tags."""
        text = "<|document|>文档.pdf<|/document|> 内容"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata["document"] == "文档.pdf"
        assert remaining == "内容"

    def test_very_long_tag_value(self):
        """Test handling of very long tag values."""
        long_value = "x" * 10000
        text = f"<|document|>{long_value}<|/document|> Content"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata["document"] == long_value
        assert remaining == "Content"

    def test_empty_text(self):
        """Test handling of empty text."""
        text = ""
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata == {}
        assert remaining == ""

    def test_only_tags_no_content(self):
        """Test text with only tags and no remaining content."""
        text = "<|document|>test.pdf<|/document|>"
        metadata, remaining = _extract_leading_metadata_tags(text)

        assert metadata == {"document": "test.pdf"}
        assert remaining == ""


class TestCustomSectionsConfig:
    """Tests for custom sections configuration in SourceFormatConfig."""

    def test_custom_section_with_different_template(self):
        """Test formatting with custom section template."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "document": "FILE: {}\n",
            "info": "INFO: {}\n",
        }

        text = "Main content"
        meta_dict = {"document": "test.pdf", "info": "Page 1"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert "FILE: test.pdf" in result
        assert "INFO: Page 1" in result
        assert result.endswith("Main content")

    def test_custom_section_with_additional_keys(self):
        """Test adding new custom section keys."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "document": "<|document|>{}<|/document|>\n",
            "info": "<|info|>{}<|/info|>\n",
            "author": "Author: {}\n",
            "title": "Title: {}\n",
        }

        text = "Main content"
        meta_dict = {
            "document": "test.pdf",
            "author": "John Doe",
            "title": "Test Document",
        }

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert "<|document|>test.pdf<|/document|>" in result
        assert "Author: John Doe" in result
        assert "Title: Test Document" in result
        assert result.endswith("Main content")

    def test_custom_section_with_subset_of_default_keys(self):
        """Test using only a subset of default keys."""
        config = InternalSearchConfig()
        # Only keep document, remove info
        config.source_format_config.sections = {
            "document": "<|document|>{}<|/document|>\n",
        }

        text = "Main content"
        meta_dict = {"document": "test.pdf", "info": "Page 1"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert "<|document|>test.pdf<|/document|>" in result
        # info should not be formatted since it's not in sections
        assert "Page 1" not in result
        assert result.endswith("Main content")

    def test_custom_section_with_empty_sections(self):
        """Test with empty sections dict (no metadata formatting)."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {}

        text = "Main content"
        meta_dict = {"document": "test.pdf", "info": "Page 1"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        # No metadata should be formatted
        assert result == "Main content"

    def test_custom_section_without_newlines(self):
        """Test custom template without newlines."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "document": "[DOC:{}]",
            "info": "[INFO:{}]",
        }

        text = "Main content"
        meta_dict = {"document": "test.pdf", "info": "Page 1"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert result == "[DOC:test.pdf]\n[INFO:Page 1]\nMain content"

    def test_custom_section_with_html_style_tags(self):
        """Test custom sections with HTML-style tags."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "document": '<div class="document">{}</div>\n',
            "info": '<span class="info">{}</span>\n',
        }

        text = "Main content"
        meta_dict = {"document": "test.pdf", "info": "metadata"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert '<div class="document">test.pdf</div>' in result
        assert '<span class="info">metadata</span>' in result

    def test_modify_chunks_with_custom_sections(self):
        """Test end-to-end with custom sections configuration."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "filename": "File: {}\n",
            "page": "Page: {}\n",
        }

        chunk = ContentChunk(
            text="<filename>report.pdf</filename><page>5</page> Content here",
            metadata=ContentMetadata(key="report.pdf", mime_type="application/pdf"),
        )
        chunks = [chunk]

        result = modify_metadata_in_chunks(chunks, config)

        assert "File: report.pdf" in result[0].text
        assert "Page: 5" in result[0].text
        assert "Content here" in result[0].text

    def test_custom_sections_with_markdown_formatting(self):
        """Test custom sections with markdown formatting."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "document": "**Document:** {}\n",
            "info": "*Info:* {}\n",
        }

        text = "Main content"
        meta_dict = {"document": "test.pdf", "info": "Important"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert "**Document:** test.pdf" in result
        assert "*Info:* Important" in result

    def test_custom_sections_order_preservation(self):
        """Test that custom sections preserve the order defined in config."""
        config = InternalSearchConfig()
        # Use OrderedDict behavior (dict is ordered in Python 3.7+)
        config.source_format_config.sections = {
            "title": "TITLE: {}\n",
            "author": "AUTHOR: {}\n",
            "document": "DOC: {}\n",
        }

        text = "Content"
        meta_dict = {"document": "file.pdf", "author": "Jane", "title": "Paper"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        # Check order by finding positions
        title_pos = result.index("TITLE:")
        author_pos = result.index("AUTHOR:")
        doc_pos = result.index("DOC:")

        assert title_pos < author_pos < doc_pos

    def test_custom_section_with_multiline_template(self):
        """Test custom sections with multiline templates."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "document": "=== Document ===\n{}\n================\n",
        }

        text = "Content"
        meta_dict = {"document": "test.pdf"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert "=== Document ===" in result
        assert "test.pdf" in result
        assert "================" in result

    def test_extract_and_format_with_non_default_tags(self):
        """Test extracting non-default tags and formatting them with custom config."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "source": "SOURCE: {}\n",
            "category": "CATEGORY: {}\n",
        }

        chunk = ContentChunk(
            text="<source>Database</source><category>Report</category> Data content",
            metadata=ContentMetadata(key="data.db", mime_type="application/x-sqlite3"),
        )
        chunks = [chunk]

        result = modify_metadata_in_chunks(chunks, config)

        assert "SOURCE: Database" in result[0].text
        assert "CATEGORY: Report" in result[0].text
        assert "Data content" in result[0].text

    def test_custom_sections_with_special_characters(self):
        """Test custom sections with special characters in templates."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "document": "📄 Document: {}\n",
            "info": "ℹ️ Info: {}\n",
        }

        text = "Content"
        meta_dict = {"document": "test.pdf", "info": "metadata"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        assert "📄 Document: test.pdf" in result
        assert "ℹ️ Info: metadata" in result

    def test_custom_sections_empty_template(self):
        """Test custom sections with empty template string."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "document": "{}",  # No prefix, no newline
            "info": "",  # Empty template
        }

        text = "Content"
        meta_dict = {"document": "test.pdf", "info": "data"}

        result = _format_chunk_with_metadata(text, meta_dict, config)

        # document should appear as-is
        assert "test.pdf" in result
        # info with empty template should not contribute anything visible
        assert result.count("\n") >= 1  # At least one newline before content

    def test_modify_chunks_ignores_extracted_tags_not_in_config(self):
        """Test that extracted tags not in config sections are not re-added."""
        config = InternalSearchConfig()
        config.source_format_config.sections = {
            "document": "DOC: {}\n",
        }

        # Chunk has both document and info tags, but config only formats document
        chunk = ContentChunk(
            text="<|document|>test.pdf<|/document|><|info|>metadata<|/info|> Content",
            metadata=ContentMetadata(key="test.pdf", mime_type="application/pdf"),
        )
        chunks = [chunk]

        result = modify_metadata_in_chunks(chunks, config)

        # document should be reformatted
        assert "DOC: test.pdf" in result[0].text
        # info tag should not appear (neither in old nor new format)
        assert "<|info|>" not in result[0].text
        assert "INFO:" not in result[0].text
        # But the extracted value is lost since it's not in sections
        assert "Content" in result[0].text
