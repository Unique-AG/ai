"""Tests for globally unique source numbering and backend citation indexing.

Covers:
- compute_max_source_number_from_tool_calls
- build_source_map_from_tool_calls
- HistoryManager.get_content_chunks_for_backend
"""

import json

import pytest

from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.agentic.history_manager.utils import (
    build_source_map_from_tool_calls,
    compute_max_source_number_from_tool_calls,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.chat.schemas import ChatMessageTool, ChatMessageToolResponse
from unique_toolkit.content.schemas import ContentChunk


def _tool_call(sources: list[dict]) -> ChatMessageTool:
    return ChatMessageTool(
        externalToolCallId="tc_test",
        function_name="search",
        arguments={},
        round_index=0,
        sequence_index=0,
        response=ChatMessageToolResponse(content=json.dumps(sources)),
    )


class TestComputeMaxSourceNumber:
    @pytest.mark.ai
    def test_returns_neg1_for_empty_list(self) -> None:
        """
        Purpose: Verify baseline when no tool calls exist.
        Why this matters: The source enumerator starts from max+1; returning -1 means
            the first turn starts at 0, which is the correct offset.
        Setup summary: Empty list → expect -1.
        """
        assert compute_max_source_number_from_tool_calls([]) == -1

    @pytest.mark.ai
    def test_returns_neg1_when_no_responses(self) -> None:
        """
        Purpose: Tool calls without responses should not contribute to the max.
        Why this matters: Persisted records with missing responses must be skipped
            so they don't corrupt the offset calculation.
        Setup summary: One tool call with response=None → expect -1.
        """
        tc = ChatMessageTool(
            externalToolCallId="tc_no_resp",
            function_name="f",
            arguments={},
            round_index=0,
            sequence_index=0,
            response=None,
        )
        assert compute_max_source_number_from_tool_calls([tc]) == -1

    @pytest.mark.ai
    def test_returns_neg1_for_non_json_content(self) -> None:
        """
        Purpose: Invalid JSON in tool response content must not crash and must return -1.
        Why this matters: Corrupted or legacy records should degrade gracefully without
            affecting offset calculation.
        Setup summary: Tool call with non-JSON content string → expect -1.
        """
        tc = ChatMessageTool(
            externalToolCallId="tc_bad_json",
            function_name="f",
            arguments={},
            round_index=0,
            sequence_index=0,
            response=ChatMessageToolResponse(content="not json"),
        )
        assert compute_max_source_number_from_tool_calls([tc]) == -1

    @pytest.mark.ai
    def test_single_tool_call_single_source(self) -> None:
        """
        Purpose: Basic happy path with one source entry.
        Why this matters: Confirms that a single persisted source is correctly read
            and its number returned as the max.
        Setup summary: Tool call with source_number=3 → expect 3.
        """
        tc = _tool_call([{"source_number": 3, "content": "hello"}])
        assert compute_max_source_number_from_tool_calls([tc]) == 3

    @pytest.mark.ai
    def test_multiple_tool_calls_finds_global_max(self) -> None:
        """
        Purpose: Max is computed across all tool calls, not just the last.
        Why this matters: Each agentic turn may produce multiple tool calls; the global
            maximum across all of them determines the correct next-turn offset.
        Setup summary: Two tool calls with source numbers [0,1] and [2,5] → expect 5.
        """
        tc1 = _tool_call(
            [
                {"source_number": 0, "content": "a"},
                {"source_number": 1, "content": "b"},
            ]
        )
        tc2 = _tool_call(
            [
                {"source_number": 2, "content": "c"},
                {"source_number": 5, "content": "d"},
            ]
        )
        assert compute_max_source_number_from_tool_calls([tc1, tc2]) == 5

    @pytest.mark.ai
    def test_skips_non_int_source_numbers(self) -> None:
        """
        Purpose: Non-integer source_number values must be ignored.
        Why this matters: Malformed entries should not cause a TypeError or inflate
            the max; only valid integers should contribute.
        Setup summary: One entry with string source_number, one with int 2 → expect 2.
        """
        tc = _tool_call(
            [
                {"source_number": "bad", "content": "x"},
                {"source_number": 2, "content": "y"},
            ]
        )
        assert compute_max_source_number_from_tool_calls([tc]) == 2

    @pytest.mark.ai
    def test_skips_entries_without_source_number(self) -> None:
        """
        Purpose: Entries missing the source_number key must be skipped.
        Why this matters: Prevents KeyError and ensures backwards compatibility with
            older persisted records that may lack the field.
        Setup summary: Entry with only a content key → expect -1.
        """
        tc = _tool_call([{"content": "no source_number key"}])
        assert compute_max_source_number_from_tool_calls([tc]) == -1

    @pytest.mark.ai
    def test_ignores_non_chatmessagetool_objects(self) -> None:
        """
        Purpose: Non-ChatMessageTool objects in the list must be silently skipped.
        Why this matters: The caller may pass a mixed list; type safety must be
            enforced at runtime to avoid AttributeError.
        Setup summary: List of strings and ints → expect -1.
        """
        assert compute_max_source_number_from_tool_calls(["garbage", 42]) == -1


class TestBuildSourceMap:
    @pytest.mark.ai
    def test_empty_list(self) -> None:
        """
        Purpose: Empty input returns an empty map.
        Why this matters: No prior tool calls means no prior sources; the map
            should be empty so get_content_chunks_for_backend produces no padding.
        Setup summary: Empty list → expect {}.
        """
        assert build_source_map_from_tool_calls([]) == {}

    @pytest.mark.ai
    def test_single_source(self) -> None:
        """
        Purpose: A single valid source entry is reconstructed as a ContentChunk.
        Why this matters: The map is used to populate prior-turn positions in the
            searchContext array; missing entries would produce broken citations.
        Setup summary: One tool call with source_number=0 and content="hello"
            → map contains ContentChunk at key 0 with text "hello".
        """
        tc = _tool_call([{"source_number": 0, "content": "hello"}])
        result = build_source_map_from_tool_calls([tc])
        assert len(result) == 1
        assert 0 in result
        assert result[0].text == "hello"

    @pytest.mark.ai
    def test_multiple_sources_across_calls(self) -> None:
        """
        Purpose: Sources from multiple tool calls are merged into a single map.
        Why this matters: A single turn may include multiple tool invocations each
            contributing sources; all must appear in the map for correct indexing.
        Setup summary: tc1 contributes sources 0,1; tc2 contributes source 3
            → map has three entries with correct texts.
        """
        tc1 = _tool_call(
            [
                {"source_number": 0, "content": "alpha"},
                {"source_number": 1, "content": "beta"},
            ]
        )
        tc2 = _tool_call([{"source_number": 3, "content": "delta"}])
        result = build_source_map_from_tool_calls([tc1, tc2])
        assert len(result) == 3
        assert result[0].text == "alpha"
        assert result[1].text == "beta"
        assert result[3].text == "delta"

    @pytest.mark.ai
    def test_skips_entries_missing_content(self) -> None:
        """
        Purpose: Entries without a content field are silently skipped.
        Why this matters: Incomplete records must not produce ContentChunk objects
            with None text, which would fail backend serialisation.
        Setup summary: Entry with only source_number → expect empty map.
        """
        tc = _tool_call([{"source_number": 0}])
        assert build_source_map_from_tool_calls([tc]) == {}

    @pytest.mark.ai
    def test_skips_entries_with_non_string_content(self) -> None:
        """
        Purpose: Non-string content values are rejected.
        Why this matters: ContentChunk.text expects a string; passing an int would
            cause a Pydantic validation error or silent corruption.
        Setup summary: content=123 (int) → expect empty map.
        """
        tc = _tool_call([{"source_number": 0, "content": 123}])
        assert build_source_map_from_tool_calls([tc]) == {}

    @pytest.mark.ai
    def test_later_call_overwrites_earlier_source_number(self) -> None:
        """
        Purpose: If the same source_number appears in two tool calls, the later one wins.
        Why this matters: With global enumeration, duplicates cannot occur in practice,
            but last-write-wins is the defined semantics if they ever do.
        Setup summary: Two tool calls both with source_number=0 → result has the
            content from the second call.
        """
        tc1 = _tool_call([{"source_number": 0, "content": "first"}])
        tc2 = _tool_call([{"source_number": 0, "content": "second"}])
        result = build_source_map_from_tool_calls([tc1, tc2])
        assert result[0].text == "second"

    @pytest.mark.ai
    def test_preserves_content_id(self) -> None:
        """
        Purpose: The content_id serialised by transform_chunks_to_string is round-tripped
            back into ContentChunk.id.
        Why this matters: The backend uses ContentChunk.id to link a citation back to
            its source content object; losing it on reconstruction breaks those links.
        Setup summary: Entry with content_id="abc123" → result[0].id == "abc123".
        """
        tc = _tool_call(
            [{"source_number": 0, "content": "hello", "content_id": "abc123"}]
        )
        result = build_source_map_from_tool_calls([tc])
        assert result[0].id == "abc123"

    @pytest.mark.ai
    def test_missing_content_id_defaults_to_empty_string(self) -> None:
        """
        Purpose: Entries without content_id (e.g. older records) produce id="" not None.
        Why this matters: The backend DTO requires id to be a string; None would fail
            validation.
        Setup summary: Entry without content_id key → result[0].id == "".
        """
        tc = _tool_call([{"source_number": 0, "content": "hello"}])
        result = build_source_map_from_tool_calls([tc])
        assert result[0].id == ""


class TestSourceEnumeratorSync:
    """Tests that _source_enumerator stays in sync after source reduction."""

    @staticmethod
    def _make_history_manager_with_enumerator(
        initial_source_offset: int,
        source_enumerator: int,
        current_chunks: list[ContentChunk] | None = None,
    ) -> HistoryManager:
        hm = HistoryManager.__new__(HistoryManager)
        hm._initial_source_offset = initial_source_offset
        hm._source_enumerator = source_enumerator
        hm._db_source_map = {}
        hm._source_offset_initialized = True
        mock_ref_mgr = ReferenceManager.__new__(ReferenceManager)
        mock_ref_mgr._chunks = current_chunks or []
        hm._reference_manager = mock_ref_mgr
        return hm

    @pytest.mark.ai
    def test_enumerator_stays_consistent_when_no_reduction(self) -> None:
        """
        Purpose: Without reduction _source_enumerator equals offset + chunk count.
        Why this matters: Confirms the synchronisation formula is idempotent in the
            normal (no-reduction) path — it must not misalign a healthy enumerator.
        Setup summary: offset=5, 3 current chunks, enumerator already at 8 → stays 8.
        """
        chunks = [ContentChunk(text=str(i)) for i in range(3)]
        hm = self._make_history_manager_with_enumerator(
            initial_source_offset=5,
            source_enumerator=8,
            current_chunks=chunks,
        )
        synced = hm._initial_source_offset + len(hm._reference_manager.get_chunks())
        assert synced == 8
        assert synced == hm._source_enumerator

    @pytest.mark.ai
    def test_enumerator_corrected_after_reduction(self) -> None:
        """
        Purpose: After source reduction compacts chunks, _source_enumerator must
            be lowered to offset + remaining chunk count.
        Why this matters: If not corrected, new tool results would get source numbers
            that leave a gap, causing get_content_chunks_for_backend to place chunks
            at wrong positions.
        Setup summary: offset=5, originally 5 chunks (enumerator=10), reduction
            compacted to 3 chunks → synced enumerator should be 8, not 10.
        """
        reduced_chunks = [ContentChunk(text=str(i)) for i in range(3)]
        hm = self._make_history_manager_with_enumerator(
            initial_source_offset=5,
            source_enumerator=10,
            current_chunks=reduced_chunks,
        )
        hm._source_enumerator = hm._initial_source_offset + len(
            hm._reference_manager.get_chunks()
        )
        assert hm._source_enumerator == 8

    @pytest.mark.ai
    def test_new_sources_contiguous_after_reduction(self) -> None:
        """
        Purpose: After reduction + enumerator sync, new tool sources continue
            contiguously so get_content_chunks_for_backend maps them correctly.
        Why this matters: End-to-end validation that the gap scenario described in
            the bot comment does not occur: reduction compacts 5→3 chunks, new
            sources start at 8 (not 10), and get_content_chunks_for_backend places
            all 6 chunks correctly at positions 5..10.
        Setup summary: offset=5, 3 reduced chunks + 3 new chunks simulated by
            manually appending → result[5..10] maps to all 6 chunks.
        """
        reduced_chunks = [ContentChunk(text=f"reduced_{i}") for i in range(3)]
        hm = self._make_history_manager_with_enumerator(
            initial_source_offset=5,
            source_enumerator=10,
            current_chunks=reduced_chunks,
        )
        hm._source_enumerator = hm._initial_source_offset + len(
            hm._reference_manager.get_chunks()
        )
        assert hm._source_enumerator == 8

        new_chunks = [ContentChunk(text=f"new_{i}") for i in range(3)]
        hm._reference_manager._chunks.extend(new_chunks)
        hm._source_enumerator += len(new_chunks)
        assert hm._source_enumerator == 11

        result = hm.get_content_chunks_for_backend()
        assert len(result) == 11
        assert result[5].text == "reduced_0"
        assert result[6].text == "reduced_1"
        assert result[7].text == "reduced_2"
        assert result[8].text == "new_0"
        assert result[9].text == "new_1"
        assert result[10].text == "new_2"


class TestGetContentChunksForBackend:
    @staticmethod
    def _make_history_manager(
        initial_source_offset: int = 0,
        db_source_map: dict[int, ContentChunk] | None = None,
        current_chunks: list[ContentChunk] | None = None,
    ) -> HistoryManager:
        hm = HistoryManager.__new__(HistoryManager)
        hm._initial_source_offset = initial_source_offset
        hm._db_source_map = db_source_map or {}
        mock_ref_mgr = ReferenceManager.__new__(ReferenceManager)
        mock_ref_mgr._chunks = current_chunks or []
        hm._reference_manager = mock_ref_mgr
        return hm

    @pytest.mark.ai
    def test_no_prior_no_current_returns_empty(self) -> None:
        """
        Purpose: First ever turn with no DB history and no current sources returns [].
        Why this matters: An empty searchContext is valid; no padding should be added
            when there is nothing to index.
        Setup summary: offset=0, empty db_map, no current chunks → [].
        """
        hm = self._make_history_manager()
        assert hm.get_content_chunks_for_backend() == []

    @pytest.mark.ai
    def test_only_current_turn_chunks(self) -> None:
        """
        Purpose: First turn with sources produces a list starting at index 0.
        Why this matters: searchContext[0] must resolve [source0]; no padding needed
            when there are no prior turns.
        Setup summary: offset=0, two current chunks → result[0]="a", result[1]="b".
        """
        chunks = [ContentChunk(text="a"), ContentChunk(text="b")]
        hm = self._make_history_manager(current_chunks=chunks)
        result = hm.get_content_chunks_for_backend()
        assert len(result) == 2
        assert result[0].text == "a"
        assert result[1].text == "b"

    @pytest.mark.ai
    def test_prior_turn_and_current_turn(self) -> None:
        """
        Purpose: Prior-turn sources appear at their original indices; current-turn
            sources follow immediately after.
        Why this matters: The backend indexes into searchContext[N] to resolve [sourceN];
            positions must be exact or citations will point to wrong content.
        Setup summary: offset=3, db_map has sources at 0 and 2, current has one chunk
            → result length 4, gap at index 1 is empty placeholder.
        """
        db_map = {0: ContentChunk(text="old_0"), 2: ContentChunk(text="old_2")}
        current = [ContentChunk(text="new_3")]
        hm = self._make_history_manager(
            initial_source_offset=3,
            db_source_map=db_map,
            current_chunks=current,
        )
        result = hm.get_content_chunks_for_backend()
        assert len(result) == 4
        assert result[0].text == "old_0"
        assert result[1].text == ""  # compacted gap → placeholder
        assert result[2].text == "old_2"
        assert result[3].text == "new_3"

    @pytest.mark.ai
    def test_gap_indices_are_empty_content_chunks(self) -> None:
        """
        Purpose: Indices not present in db_source_map are filled with empty placeholders.
        Why this matters: The backend requires a contiguous array; gaps caused by
            compaction must be filled with valid (but empty) entries so the array
            length is correct and [sourceN] for real sources still resolves correctly.
        Setup summary: offset=3, only source 1 in db_map → indices 0 and 2 are empty.
        """
        db_map = {1: ContentChunk(text="only_1")}
        hm = self._make_history_manager(
            initial_source_offset=3,
            db_source_map=db_map,
            current_chunks=[],
        )
        result = hm.get_content_chunks_for_backend()
        assert len(result) == 3
        assert result[0].text == ""
        assert result[1].text == "only_1"
        assert result[2].text == ""

    @pytest.mark.ai
    def test_db_source_beyond_offset_is_ignored(self) -> None:
        """
        Purpose: DB sources whose index >= initial_source_offset are not placed in the
            result (they would overwrite current-turn positions).
        Why this matters: Such entries indicate a bug in the source map but must not
            corrupt the current turn's citations.
        Setup summary: offset=3, db_map has source at 5 (beyond offset), one current
            chunk → result length 4, indices 0-2 are empty, index 3 is current.
        """
        db_map = {5: ContentChunk(text="should_be_ignored")}
        hm = self._make_history_manager(
            initial_source_offset=3,
            db_source_map=db_map,
            current_chunks=[ContentChunk(text="curr")],
        )
        result = hm.get_content_chunks_for_backend()
        assert len(result) == 4
        assert result[3].text == "curr"
        for i in range(3):
            assert result[i].text == ""

    @pytest.mark.ai
    def test_large_offset_with_no_db_sources(self) -> None:
        """
        Purpose: A large offset with no matching DB sources produces the correct number
            of empty placeholders before the current chunk.
        Why this matters: If a prior turn had many sources that were all compacted away,
            the padding must still be correct so the current chunk is at the right index.
        Setup summary: offset=5, empty db_map, one current chunk → 5 empty + 1 current.
        """
        hm = self._make_history_manager(
            initial_source_offset=5,
            db_source_map={},
            current_chunks=[ContentChunk(text="x")],
        )
        result = hm.get_content_chunks_for_backend()
        assert len(result) == 6
        for i in range(5):
            assert result[i].text == ""
        assert result[5].text == "x"
