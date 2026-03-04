"""Tests for reference resolution: source numbering round-trip.

Verifies that source numbers assigned by transform_chunks_to_string
are correctly resolved back to the right chunks by _find_references,
regardless of whether 0-based or 1-based numbering is used.
"""

import pytest

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.reference import (
    _extract_numbers_in_brackets,
    _find_references,
    _preprocess_message,
)


def _make_chunk(id: str, title: str) -> ContentChunk:
    return ContentChunk(
        id=id,
        chunk_id=None,
        key=id,
        title=title,
        text=f"content of {title}",
        start_page=1,
        end_page=1,
        order=0,
        object="search_result",
        url=None,
        internally_stored_at=None,
    )


class TestPreprocessSourceFormats:
    """Verify that _preprocess_message normalizes [sourceN] to [N]."""

    def test_source0_becomes_bracket_0(self):
        result = _preprocess_message("fact [source0].")
        nums = _extract_numbers_in_brackets(result)
        assert 0 in nums

    def test_source_space_1_becomes_bracket_1(self):
        result = _preprocess_message("fact [source 1].")
        nums = _extract_numbers_in_brackets(result)
        assert 1 in nums

    def test_source_underscore_2_becomes_bracket_2(self):
        result = _preprocess_message("fact source_2.")
        nums = _extract_numbers_in_brackets(result)
        assert 2 in nums


class TestFindReferencesIndexing:
    """Core tests for the 0-based vs 1-based indexing bug."""

    def test_source0_resolves_to_first_chunk(self):
        """[source0] must resolve to the first chunk, not be silently dropped."""
        chunk = _make_chunk("id0", "First Source")
        preprocessed = _preprocess_message("Some fact [source0].")
        refs = _find_references(
            text=preprocessed, search_context=[chunk], message_id="msg"
        )
        assert len(refs) == 1, "source0 citation was silently dropped"
        assert refs[0].id == "id0"

    def test_bracket_0_resolves_to_first_chunk(self):
        """[0] must resolve to the first chunk when sources are 0-based."""
        chunk = _make_chunk("id0", "First Source")
        refs = _find_references(
            text="Some fact [0].", search_context=[chunk], message_id="msg"
        )
        assert len(refs) == 1, "[0] citation was silently dropped"
        assert refs[0].id == "id0"

    def test_all_zero_based_sources_are_resolvable(self):
        """With 0-based source numbering, every chunk must be reachable."""
        chunks = [_make_chunk(f"id{i}", f"Title {i}") for i in range(3)]
        llm_text = "Fact A [source0]. Fact B [source1]. Fact C [source2]."
        preprocessed = _preprocess_message(llm_text)
        refs = _find_references(
            text=preprocessed, search_context=chunks, message_id="msg"
        )
        resolved_ids = {r.id for r in refs}
        assert resolved_ids == {"id0", "id1", "id2"}, (
            f"Expected all 3 chunks resolved, got {resolved_ids}"
        )

    def test_multi_turn_offset_sources_resolve_correctly(self):
        """With prior chunks, new source numbers must map to the correct chunks.

        Scenario: 3 prior chunks exist, new tool call adds 2 more.
        transform_chunks_to_string would label them source3 and source4.
        The full search_context has indices 0-4, so source3 -> index 3,
        source4 -> index 4.
        """
        prior_chunks = [_make_chunk(f"prior{i}", f"Prior {i}") for i in range(3)]
        new_chunks = [_make_chunk(f"new{i}", f"New {i}") for i in range(2)]
        all_chunks = prior_chunks + new_chunks

        llm_text = "Fact A [source3]. Fact B [source4]."
        preprocessed = _preprocess_message(llm_text)
        refs = _find_references(
            text=preprocessed, search_context=all_chunks, message_id="msg"
        )
        resolved_ids = {r.id for r in refs}
        assert resolved_ids == {"new0", "new1"}, (
            f"Expected new chunks, got {resolved_ids} (off-by-one?)"
        )

    def test_one_based_sources_still_work(self):
        """1-based numbering (the existing assumption) should still resolve correctly."""
        chunks = [_make_chunk(f"id{i}", f"Title {i}") for i in range(3)]
        refs = _find_references(
            text="Fact [1]. Fact [2]. Fact [3].",
            search_context=chunks,
            message_id="msg",
        )
        resolved_ids = {r.id for r in refs}
        assert resolved_ids == {"id0", "id1", "id2"}
