from unique_toolkit.content.schemas import ContentChunk, ContentMetadata

from unique_internal_search.utils import (
    _append_metadata_in_chunk,
    append_metadata_in_chunks,
)


class TestAppendMetadataInChunks:
    """Tests for append_metadata_in_chunks function"""

    def test_append_metadata_with_none_metadata_sections(self):
        """Test that chunks are returned unchanged when metadata_sections is None"""
        chunks = [
            ContentChunk(
                id="cont_123",
                text="Original text",
                order=1,
                metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
            )
        ]

        result = append_metadata_in_chunks(chunks, metadata_sections=None)

        assert len(result) == 1
        assert result[0].text == "Original text"

    def test_append_metadata_with_empty_metadata_sections(self):
        """Test that chunks are returned unchanged when metadata_sections is empty"""
        chunks = [
            ContentChunk(
                id="cont_123",
                text="Original text",
                order=1,
                metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
            )
        ]

        result = append_metadata_in_chunks(chunks, metadata_sections={})

        assert len(result) == 1
        assert result[0].text == "Original text"

    def test_append_metadata_with_none_chunk_metadata(self):
        """Test that chunks without metadata are skipped"""
        chunks = [
            ContentChunk(
                id="cont_123",
                text="Original text",
                order=1,
                metadata=None,
            )
        ]

        result = append_metadata_in_chunks(chunks, metadata_sections={"key": "Key: {}"})

        assert len(result) == 1
        assert result[0].text == "Original text"

    def test_append_metadata_with_matching_keys(self):
        """Test that metadata is correctly prepended when keys match"""
        chunks = [
            ContentChunk(
                id="cont_123",
                text="Original text",
                order=1,
                metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
            )
        ]

        result = append_metadata_in_chunks(
            chunks, metadata_sections={"key": "Document: {}"}
        )

        assert len(result) == 1
        assert result[0].text == "Document: doc.pdf\nOriginal text"

    def test_append_metadata_with_multiple_keys(self):
        """Test that multiple metadata fields are correctly prepended"""
        chunks = [
            ContentChunk(
                id="cont_123",
                text="Original text",
                order=1,
                metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
            )
        ]

        result = append_metadata_in_chunks(
            chunks,
            metadata_sections={
                "key": "File: {}",
                "mimeType": "Type: {}",
            },
        )

        assert len(result) == 1
        expected_text = "File: doc.pdf\nType: application/pdf\nOriginal text"
        assert result[0].text == expected_text

    def test_append_metadata_with_non_matching_keys(self):
        """Test that non-matching metadata keys are ignored"""
        chunks = [
            ContentChunk(
                id="cont_123",
                text="Original text",
                order=1,
                metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
            )
        ]

        result = append_metadata_in_chunks(
            chunks, metadata_sections={"nonexistent": "Value: {}"}
        )

        assert len(result) == 1
        assert result[0].text == "Original text"

    def test_append_metadata_with_multiple_chunks(self):
        """Test that metadata is appended to all chunks"""
        chunks = [
            ContentChunk(
                id="cont_123",
                text="First chunk",
                order=1,
                metadata=ContentMetadata(key="doc1.pdf", mime_type="application/pdf"),
            ),
            ContentChunk(
                id="cont_456",
                text="Second chunk",
                order=2,
                metadata=ContentMetadata(key="doc2.pdf", mime_type="application/pdf"),
            ),
        ]

        result = append_metadata_in_chunks(
            chunks, metadata_sections={"key": "Document: {}"}
        )

        assert len(result) == 2
        assert result[0].text == "Document: doc1.pdf\nFirst chunk"
        assert result[1].text == "Document: doc2.pdf\nSecond chunk"

    def test_append_metadata_with_mixed_chunks(self):
        """Test with a mix of chunks with and without metadata"""
        chunks = [
            ContentChunk(
                id="cont_123",
                text="First chunk",
                order=1,
                metadata=ContentMetadata(key="doc1.pdf", mime_type="application/pdf"),
            ),
            ContentChunk(
                id="cont_456",
                text="Second chunk",
                order=2,
                metadata=None,
            ),
            ContentChunk(
                id="cont_789",
                text="Third chunk",
                order=3,
                metadata=ContentMetadata(key="doc3.pdf", mime_type="text/plain"),
            ),
        ]

        result = append_metadata_in_chunks(
            chunks, metadata_sections={"key": "Document: {}"}
        )

        assert len(result) == 3
        assert result[0].text == "Document: doc1.pdf\nFirst chunk"
        assert result[1].text == "Second chunk"
        assert result[2].text == "Document: doc3.pdf\nThird chunk"


class TestAppendMetadataInChunk:
    """Tests for _append_metadata_in_chunk private function"""

    def test_append_metadata_basic(self):
        """Test basic metadata appending"""

        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=1,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(chunk, metadata_sections={"key": "File: {}"})

        assert result.text == "File: doc.pdf\nOriginal text"

    def test_append_metadata_with_custom_template(self):
        """Test with custom formatting templates"""
        from unique_internal_search.utils import _append_metadata_in_chunk

        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=1,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(
            chunk, metadata_sections={"key": "### Filename: {}\n---"}
        )

        assert result.text == "### Filename: doc.pdf\n---\nOriginal text"

    def test_append_metadata_preserves_other_fields(self):
        """Test that other chunk fields are preserved"""
        from unique_internal_search.utils import _append_metadata_in_chunk

        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=5,
            title="Test Title",
            start_page=10,
            end_page=15,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(chunk, metadata_sections={"key": "File: {}"})

        assert result.id == "cont_123"
        assert result.order == 5
        assert result.title == "Test Title"
        assert result.start_page == 10
        assert result.end_page == 15
        assert result.metadata.key == "doc.pdf"

    def test_append_metadata_with_empty_sections(self):
        """Test that empty metadata sections leave text unchanged"""
        from unique_internal_search.utils import _append_metadata_in_chunk

        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=1,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(chunk, metadata_sections={})

        assert result.text == "Original text"

    def test_append_metadata_returns_chunk(self):
        """Test that function returns a ContentChunk object"""
        from unique_internal_search.utils import _append_metadata_in_chunk

        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=1,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(chunk, metadata_sections={"key": "File: {}"})

        assert isinstance(result, ContentChunk)

    def test_append_metadata_with_camel_case_key(self):
        """Test that camelCase keys (from model_dump by_alias) work correctly"""
        from unique_internal_search.utils import _append_metadata_in_chunk

        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=1,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(
            chunk, metadata_sections={"mimeType": "MIME Type: {}"}
        )

        assert result.text == "MIME Type: application/pdf\nOriginal text"
