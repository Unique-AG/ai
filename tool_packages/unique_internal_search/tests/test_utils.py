from unique_toolkit.content.schemas import ContentChunk, ContentMetadata

from unique_internal_search.utils import (
    SearchStringResult,
    _append_metadata_in_chunk,
    _deduplicate_search_results,
    append_metadata_in_chunks,
    clean_search_string,
    interleave_search_results_round_robin,
)


class TestAppendMetadataInChunks:
    """Tests for append_metadata_in_chunks function"""

    def test_append_metadata_with_none_metadata_sections(self):
        """Test that chunks are returned unchanged when metadata_chunk_sections is None"""
        chunks = [
            ContentChunk(
                id="cont_123",
                text="Original text",
                order=1,
                metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
            )
        ]

        result = append_metadata_in_chunks(chunks, metadata_chunk_sections=None)

        assert len(result) == 1
        assert result[0].text == "Original text"

    def test_append_metadata_with_empty_metadata_sections(self):
        """Test that chunks are returned unchanged when metadata_chunk_sections is empty"""
        chunks = [
            ContentChunk(
                id="cont_123",
                text="Original text",
                order=1,
                metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
            )
        ]

        result = append_metadata_in_chunks(chunks, metadata_chunk_sections={})

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

        result = append_metadata_in_chunks(
            chunks, metadata_chunk_sections={"key": "Key: {}"}
        )

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
            chunks, metadata_chunk_sections={"key": "Document: {}"}
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
            metadata_chunk_sections={
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
            chunks, metadata_chunk_sections={"nonexistent": "Value: {}"}
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
            chunks, metadata_chunk_sections={"key": "Document: {}"}
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
            chunks, metadata_chunk_sections={"key": "Document: {}"}
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

        result = _append_metadata_in_chunk(
            chunk, metadata_chunk_sections={"key": "File: {}"}
        )

        assert result.text == "File: doc.pdf\nOriginal text"

    def test_append_metadata_with_custom_template(self):
        """Test with custom formatting templates"""
        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=1,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(
            chunk, metadata_chunk_sections={"key": "### Filename: {}\n---"}
        )

        assert result.text == "### Filename: doc.pdf\n---\nOriginal text"

    def test_append_metadata_preserves_other_fields(self):
        """Test that other chunk fields are preserved"""
        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=5,
            title="Test Title",
            start_page=10,
            end_page=15,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(
            chunk, metadata_chunk_sections={"key": "File: {}"}
        )

        assert result.id == "cont_123"
        assert result.order == 5
        assert result.title == "Test Title"
        assert result.start_page == 10
        assert result.end_page == 15
        assert result.metadata is not None
        assert result.metadata.key == "doc.pdf"

    def test_append_metadata_with_empty_sections(self):
        """Test that empty metadata sections leave text unchanged"""
        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=1,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(chunk, metadata_chunk_sections={})

        assert result.text == "Original text"

    def test_append_metadata_returns_chunk(self):
        """Test that function returns a ContentChunk object"""
        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=1,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(
            chunk, metadata_chunk_sections={"key": "File: {}"}
        )

        assert isinstance(result, ContentChunk)

    def test_append_metadata_with_camel_case_key(self):
        """Test that camelCase keys (from model_dump by_alias) work correctly"""
        chunk = ContentChunk(
            id="cont_123",
            text="Original text",
            order=1,
            metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
        )

        result = _append_metadata_in_chunk(
            chunk, metadata_chunk_sections={"mimeType": "MIME Type: {}"}
        )

        assert result.text == "MIME Type: application/pdf\nOriginal text"


class TestInterleaveSearchResultsRoundRobin:
    """Tests for interleave_search_results_round_robin function"""

    def test_empty_list(self):
        """Test that empty list returns empty list"""
        result = interleave_search_results_round_robin([])
        assert result == []

    def test_single_search_result(self):
        """Test with a single search result"""
        chunks = [
            ContentChunk(
                id="chunk_1",
                chunk_id="chunk_1",
                text="First chunk",
                order=1,
                metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
            ),
            ContentChunk(
                id="chunk_2",
                chunk_id="chunk_2",
                text="Second chunk",
                order=2,
                metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
            ),
        ]
        search_results = [SearchStringResult(query="query1", chunks=chunks)]

        result = interleave_search_results_round_robin(search_results)

        assert len(result) == 2
        assert result[0].query == "query1"
        assert result[0].chunks[0].id == "chunk_1"
        assert result[1].query == "query1"
        assert result[1].chunks[0].id == "chunk_2"

    def test_multiple_results_equal_chunks(self):
        """Test interleaving with multiple search results having equal number of chunks"""
        chunks_q1 = [
            ContentChunk(
                id="A",
                chunk_id="A",
                text="Chunk A",
                order=1,
                metadata=ContentMetadata(key="doc1.pdf", mime_type="application/pdf"),
            ),
            ContentChunk(
                id="B",
                chunk_id="B",
                text="Chunk B",
                order=2,
                metadata=ContentMetadata(key="doc1.pdf", mime_type="application/pdf"),
            ),
        ]
        chunks_q2 = [
            ContentChunk(
                id="C",
                chunk_id="C",
                text="Chunk C",
                order=1,
                metadata=ContentMetadata(key="doc2.pdf", mime_type="application/pdf"),
            ),
            ContentChunk(
                id="D",
                chunk_id="D",
                text="Chunk D",
                order=2,
                metadata=ContentMetadata(key="doc2.pdf", mime_type="application/pdf"),
            ),
        ]

        search_results = [
            SearchStringResult(query="query1", chunks=chunks_q1),
            SearchStringResult(query="query2", chunks=chunks_q2),
        ]

        result = interleave_search_results_round_robin(search_results)

        # Should interleave: A, C, B, D
        assert len(result) == 4
        assert result[0].chunks[0].id == "A"
        assert result[1].chunks[0].id == "C"
        assert result[2].chunks[0].id == "B"
        assert result[3].chunks[0].id == "D"

    def test_multiple_results_different_chunk_counts(self):
        """Test interleaving with different numbers of chunks per query"""
        chunks_q1 = [
            ContentChunk(
                id="A", chunk_id="A", text="A", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="B", chunk_id="B", text="B", order=2, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="C", chunk_id="C", text="C", order=3, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
        ]
        chunks_q2 = [
            ContentChunk(
                id="D", chunk_id="D", text="D", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
        ]
        chunks_q3 = [
            ContentChunk(
                id="E", chunk_id="E", text="E", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="F", chunk_id="F", text="F", order=2, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
        ]

        search_results = [
            SearchStringResult(query="query1", chunks=chunks_q1),
            SearchStringResult(query="query2", chunks=chunks_q2),
            SearchStringResult(query="query3", chunks=chunks_q3),
        ]

        result = interleave_search_results_round_robin(search_results)

        # Expected order: A, D, E (round 1), B, F (round 2), C (round 3)
        assert len(result) == 6
        assert result[0].chunks[0].id == "A"
        assert result[1].chunks[0].id == "D"
        assert result[2].chunks[0].id == "E"
        assert result[3].chunks[0].id == "B"
        assert result[4].chunks[0].id == "F"
        assert result[5].chunks[0].id == "C"

    def test_docstring_example(self):
        """Test the example from the function's docstring"""
        chunks_q1 = [
            ContentChunk(
                id="A", chunk_id="A", text="A", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="B", chunk_id="B", text="B", order=2, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="C", chunk_id="C", text="C", order=3, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
        ]
        chunks_q2 = [
            ContentChunk(
                id="D", chunk_id="D", text="D", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="E", chunk_id="E", text="E", order=2, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
        ]
        chunks_q3 = [
            ContentChunk(
                id="F", chunk_id="F", text="F", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="G", chunk_id="G", text="G", order=2, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="H", chunk_id="H", text="H", order=3, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="I", chunk_id="I", text="I", order=4, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
        ]

        search_results = [
            SearchStringResult(query="query1", chunks=chunks_q1),
            SearchStringResult(query="query2", chunks=chunks_q2),
            SearchStringResult(query="query3", chunks=chunks_q3),
        ]

        result = interleave_search_results_round_robin(search_results)

        # Expected: A, D, F, B, E, G, C, H, I
        assert len(result) == 9
        expected_ids = ["A", "D", "F", "B", "E", "G", "C", "H", "I"]
        actual_ids = [r.chunks[0].id for r in result]
        assert actual_ids == expected_ids

    def test_deduplication_during_interleaving(self):
        """Test that duplicate chunks are removed during interleaving"""
        # Create chunks where "B" appears in both queries
        chunks_q1 = [
            ContentChunk(
                id="A", chunk_id="A", text="A", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="B", chunk_id="B", text="B", order=2, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
        ]
        chunks_q2 = [
            ContentChunk(
                id="B", chunk_id="B", text="B", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),  # Duplicate
            ContentChunk(
                id="C", chunk_id="C", text="C", order=2, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
        ]

        search_results = [
            SearchStringResult(query="query1", chunks=chunks_q1),
            SearchStringResult(query="query2", chunks=chunks_q2),
        ]

        result = interleave_search_results_round_robin(search_results)

        # Should be A, B (first occurrence), C
        # The second B should be deduplicated
        assert len(result) == 3
        assert result[0].chunks[0].id == "A"
        assert result[1].chunks[0].id == "B"
        assert result[2].chunks[0].id == "C"

    def test_chunks_without_id(self):
        """Test handling of chunks without chunk_id (None)"""
        chunks = [
            ContentChunk(
                id="content_1",
                text="Chunk without chunk_id",
                order=1,
                metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf"),
            ),
        ]
        search_results = [SearchStringResult(query="query1", chunks=chunks)]

        result = interleave_search_results_round_robin(search_results)

        # Should skip chunks without chunk_id during deduplication
        assert len(result) == 0


class TestDeduplicateSearchResults:
    """Tests for _deduplicate_search_results private function"""

    def test_no_duplicates(self):
        """Test that unique chunks are all preserved"""
        chunks = [
            ContentChunk(
                id="A", chunk_id="A", text="A", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="B", chunk_id="B", text="B", order=2, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
            ContentChunk(
                id="C", chunk_id="C", text="C", order=3, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
            ),
        ]
        search_results = [
            SearchStringResult(query="query1", chunks=[chunks[0]]),
            SearchStringResult(query="query2", chunks=[chunks[1]]),
            SearchStringResult(query="query3", chunks=[chunks[2]]),
        ]

        result = _deduplicate_search_results(search_results)

        assert len(result) == 3
        assert result[0].chunks[0].id == "A"
        assert result[1].chunks[0].id == "B"
        assert result[2].chunks[0].id == "C"

    def test_with_duplicates(self):
        """Test that duplicate chunks are removed keeping first occurrence"""
        chunk_a = ContentChunk(
            id="A", chunk_id="A", text="A", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
        )
        chunk_b = ContentChunk(
            id="B", chunk_id="B", text="B", order=2, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
        )
        chunk_a_dup = ContentChunk(
            id="A", chunk_id="A", text="A duplicate", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
        )

        search_results = [
            SearchStringResult(query="query1", chunks=[chunk_a]),
            SearchStringResult(query="query2", chunks=[chunk_b]),
            SearchStringResult(query="query3", chunks=[chunk_a_dup]),  # Duplicate
        ]

        result = _deduplicate_search_results(search_results)

        # Should keep first A and B, but not the duplicate A
        assert len(result) == 2
        assert result[0].chunks[0].id == "A"
        assert result[0].chunks[0].text == "A"  # First occurrence
        assert result[1].chunks[0].id == "B"

    def test_all_duplicates(self):
        """Test when all chunks are duplicates after the first"""
        chunk_a = ContentChunk(
            id="A", chunk_id="A", text="A", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
        )

        search_results = [
            SearchStringResult(query="query1", chunks=[chunk_a]),
            SearchStringResult(query="query2", chunks=[chunk_a]),
            SearchStringResult(query="query3", chunks=[chunk_a]),
        ]

        result = _deduplicate_search_results(search_results)

        # Should only keep the first one
        assert len(result) == 1
        assert result[0].chunks[0].id == "A"

    def test_none_id(self):
        """Test handling of chunks with None as chunk_id"""
        chunk_none = ContentChunk(
            id="content_1", text="No chunk_id", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
        )

        search_results = [
            SearchStringResult(query="query1", chunks=[chunk_none]),
        ]

        result = _deduplicate_search_results(search_results)

        # Chunks without chunk_id should be skipped
        assert len(result) == 0

    def test_mixed_none_and_valid_ids(self):
        """Test mix of chunks with and without chunk_ids"""
        chunk_with_id = ContentChunk(
            id="A", chunk_id="A", text="A", order=1, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
        )
        chunk_no_chunk_id = ContentChunk(
            id="content_2", text="No chunk_id", order=2, metadata=ContentMetadata(key="doc.pdf", mime_type="application/pdf")
        )

        search_results = [
            SearchStringResult(query="query1", chunks=[chunk_with_id]),
            SearchStringResult(query="query2", chunks=[chunk_no_chunk_id]),
            SearchStringResult(query="query3", chunks=[chunk_with_id]),  # Duplicate
        ]

        result = _deduplicate_search_results(search_results)

        # Should keep only the chunk with valid chunk_id (first occurrence)
        assert len(result) == 1
        assert result[0].chunks[0].id == "A"


class TestCleanSearchString:
    """Tests for clean_search_string function"""

    def test_remove_qdf_operator(self):
        """Test removal of QDF operator"""
        search_string = "performance benchmark --QDF=1"
        result = clean_search_string(search_string)
        assert result == "performance benchmark"

    def test_remove_boost_operators(self):
        """Test removal of boost operators"""
        search_string = "+(GPT4) performance on +(MMLU) benchmark"
        result = clean_search_string(search_string)
        assert result == "GPT4 performance on MMLU benchmark"

    def test_docstring_example_1(self):
        """Test first example from docstring"""
        search_string = "+(GPT4) performance on +(MMLU) benchmark --QDF=1"
        result = clean_search_string(search_string)
        assert result == "GPT4 performance on MMLU benchmark"

    def test_docstring_example_2(self):
        """Test second example from docstring"""
        search_string = (
            "Best practices for +(security) and +(privacy) for +(cloud storage) --QDF=2"
        )
        result = clean_search_string(search_string)
        assert result == "Best practices for security and privacy for cloud storage"

    def test_remove_both_operators(self):
        """Test removal of both QDF and boost operators"""
        search_string = "+(machine learning) models --QDF=5"
        result = clean_search_string(search_string)
        assert result == "machine learning models"

    def test_multiple_boost_operators(self):
        """Test removal of multiple boost operators"""
        search_string = "+(AI) and +(ML) for +(data science)"
        result = clean_search_string(search_string)
        assert result == "AI and ML for data science"

    def test_extra_whitespace_cleanup(self):
        """Test cleanup of extra whitespace"""
        search_string = "+(test)    multiple    spaces   --QDF=1"
        result = clean_search_string(search_string)
        assert result == "test multiple spaces"

    def test_no_operators(self):
        """Test string without any operators"""
        search_string = "simple search query"
        result = clean_search_string(search_string)
        assert result == "simple search query"

    def test_empty_string(self):
        """Test empty string"""
        result = clean_search_string("")
        assert result == ""

    def test_only_qdf_operator(self):
        """Test string with only QDF operator"""
        search_string = "--QDF=3"
        result = clean_search_string(search_string)
        assert result == ""

    def test_only_boost_operator(self):
        """Test string with only boost operator"""
        search_string = "+(query)"
        result = clean_search_string(search_string)
        assert result == "query"

    def test_qdf_with_different_numbers(self):
        """Test QDF operator with different numbers"""
        search_string_1 = "search --QDF=10"
        result_1 = clean_search_string(search_string_1)
        assert result_1 == "search"

        search_string_2 = "another search --QDF=999"
        result_2 = clean_search_string(search_string_2)
        assert result_2 == "another search"

    def test_boost_with_special_characters(self):
        """Test boost operators containing special characters"""
        search_string = "+(C++) programming and +(Node.js) framework"
        result = clean_search_string(search_string)
        assert result == "C++ programming and Node.js framework"

    def test_nested_parentheses(self):
        """Test that nested parentheses are handled correctly"""
        # The regex should only match +(...) patterns
        search_string = "+(term1) and (regular parentheses)"
        result = clean_search_string(search_string)
        assert result == "term1 and (regular parentheses)"

    def test_leading_trailing_whitespace(self):
        """Test that leading and trailing whitespace is stripped"""
        search_string = "  +(search) query  --QDF=1  "
        result = clean_search_string(search_string)
        assert result == "search query"
