"""Tests for globally unique source numbering and backend citation indexing.

Covers:
- compute_max_source_number_from_tool_calls
- build_source_map_from_tool_calls
- HistoryManager.get_content_chunks_for_backend
"""

import json

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
    def test_returns_neg1_for_empty_list(self) -> None:
        assert compute_max_source_number_from_tool_calls([]) == -1

    def test_returns_neg1_when_no_responses(self) -> None:
        tc = ChatMessageTool(
            externalToolCallId="tc_no_resp",
            function_name="f",
            arguments={},
            round_index=0,
            sequence_index=0,
            response=None,
        )
        assert compute_max_source_number_from_tool_calls([tc]) == -1

    def test_returns_neg1_for_non_json_content(self) -> None:
        tc = ChatMessageTool(
            externalToolCallId="tc_bad_json",
            function_name="f",
            arguments={},
            round_index=0,
            sequence_index=0,
            response=ChatMessageToolResponse(content="not json"),
        )
        assert compute_max_source_number_from_tool_calls([tc]) == -1

    def test_single_tool_call_single_source(self) -> None:
        tc = _tool_call([{"source_number": 3, "content": "hello"}])
        assert compute_max_source_number_from_tool_calls([tc]) == 3

    def test_multiple_tool_calls_finds_global_max(self) -> None:
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

    def test_skips_non_int_source_numbers(self) -> None:
        tc = _tool_call(
            [
                {"source_number": "bad", "content": "x"},
                {"source_number": 2, "content": "y"},
            ]
        )
        assert compute_max_source_number_from_tool_calls([tc]) == 2

    def test_skips_entries_without_source_number(self) -> None:
        tc = _tool_call([{"content": "no source_number key"}])
        assert compute_max_source_number_from_tool_calls([tc]) == -1

    def test_ignores_non_chatmessagetool_objects(self) -> None:
        assert compute_max_source_number_from_tool_calls(["garbage", 42]) == -1


class TestBuildSourceMap:
    def test_empty_list(self) -> None:
        assert build_source_map_from_tool_calls([]) == {}

    def test_single_source(self) -> None:
        tc = _tool_call([{"source_number": 0, "content": "hello"}])
        result = build_source_map_from_tool_calls([tc])
        assert len(result) == 1
        assert 0 in result
        assert result[0].text == "hello"

    def test_multiple_sources_across_calls(self) -> None:
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

    def test_skips_entries_missing_content(self) -> None:
        tc = _tool_call([{"source_number": 0}])
        assert build_source_map_from_tool_calls([tc]) == {}

    def test_skips_entries_with_non_string_content(self) -> None:
        tc = _tool_call([{"source_number": 0, "content": 123}])
        assert build_source_map_from_tool_calls([tc]) == {}

    def test_later_call_overwrites_earlier_source_number(self) -> None:
        tc1 = _tool_call([{"source_number": 0, "content": "first"}])
        tc2 = _tool_call([{"source_number": 0, "content": "second"}])
        result = build_source_map_from_tool_calls([tc1, tc2])
        assert result[0].text == "second"

    def test_preserves_content_id(self) -> None:
        tc = _tool_call(
            [{"source_number": 0, "content": "hello", "content_id": "abc123"}]
        )
        result = build_source_map_from_tool_calls([tc])
        assert result[0].id == "abc123"

    def test_missing_content_id_defaults_to_empty_string(self) -> None:
        tc = _tool_call([{"source_number": 0, "content": "hello"}])
        result = build_source_map_from_tool_calls([tc])
        assert result[0].id == ""


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

    def test_no_prior_no_current_returns_empty(self) -> None:
        hm = self._make_history_manager()
        assert hm.get_content_chunks_for_backend() == []

    def test_only_current_turn_chunks(self) -> None:
        chunks = [ContentChunk(text="a"), ContentChunk(text="b")]
        hm = self._make_history_manager(current_chunks=chunks)
        result = hm.get_content_chunks_for_backend()
        assert len(result) == 2
        assert result[0].text == "a"
        assert result[1].text == "b"

    def test_prior_turn_and_current_turn(self) -> None:
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
        assert result[1].text == ""  # gap => empty ContentChunk
        assert result[2].text == "old_2"
        assert result[3].text == "new_3"

    def test_gap_indices_are_empty_content_chunks(self) -> None:
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

    def test_db_source_beyond_offset_is_ignored(self) -> None:
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

    def test_large_offset_with_no_db_sources(self) -> None:
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
