"""
Tests for history_construction_with_contents.

Covers _extract_referenced_source_numbers, _trim_tool_content_to_used_sources,
and _append_last_tool_calls_and_tool_message (idempotency and source trimming).
"""

import json

import pytest

from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    _append_last_tool_calls_and_tool_message,
    _extract_referenced_source_numbers,
    _trim_tool_content_to_used_sources,
)
from unique_toolkit.language_model.schemas import LanguageModelMessages


class TestExtractReferencedSourceNumbers:
    """Tests for _extract_referenced_source_numbers."""

    def test_extracts_single_source(self):
        assert _extract_referenced_source_numbers("The price is $150 [source0].") == {
            0
        }

    def test_extracts_multiple_sources(self):
        assert _extract_referenced_source_numbers(
            "See [source0] and [source1] and [source5]."
        ) == {0, 1, 5}

    def test_extracts_case_insensitive(self):
        assert _extract_referenced_source_numbers("[SOURCE0] and [Source1]") == {
            0,
            1,
        }

    def test_returns_empty_for_none(self):
        assert _extract_referenced_source_numbers(None) == set()

    def test_returns_empty_for_empty_string(self):
        assert _extract_referenced_source_numbers("") == set()

    def test_returns_empty_when_no_citations(self):
        assert _extract_referenced_source_numbers("No sources here.") == set()

    def test_deduplicates_repeated_citations(self):
        assert _extract_referenced_source_numbers("[source1][source1][source1]") == {
            1
        }


class TestTrimToolContentToUsedSources:
    """Tests for _trim_tool_content_to_used_sources."""

    def test_returns_unchanged_when_no_original_content(self):
        tool_content = json.dumps(
            [
                {"source_number": 0, "content": "A"},
                {"source_number": 1, "content": "B"},
            ]
        )
        assert _trim_tool_content_to_used_sources(None, tool_content) == tool_content

    def test_returns_unchanged_when_no_referenced_sources(self):
        tool_content = json.dumps(
            [
                {"source_number": 0, "content": "A"},
                {"source_number": 1, "content": "B"},
            ]
        )
        assert _trim_tool_content_to_used_sources("No citations here.", tool_content) == tool_content

    def test_returns_unchanged_for_empty_or_invalid_tool_content(self):
        assert _trim_tool_content_to_used_sources(" [source0] ", None) == ""
        assert _trim_tool_content_to_used_sources(" [source0] ", "") == ""

    def test_keeps_only_referenced_sources_list(self):
        tool_content = json.dumps(
            [
                {"source_number": 0, "content": "A"},
                {"source_number": 1, "content": "B"},
                {"source_number": 2, "content": "C"},
            ]
        )
        original_content = "Use [source0] and [source2] only."
        result = _trim_tool_content_to_used_sources(original_content, tool_content)
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["source_number"] == 0 and parsed[0]["content"] == "A"
        assert parsed[1]["source_number"] == 2 and parsed[1]["content"] == "C"

    def test_returns_no_relevant_sources_when_none_referenced(self):
        tool_content = json.dumps(
            [{"source_number": 0, "content": "A"}, {"source_number": 1, "content": "B"}]
        )
        original_content = "Only [source5] and [source10]."
        result = _trim_tool_content_to_used_sources(original_content, tool_content)
        assert result == "No relevant sources found."

    def test_single_object_kept_when_referenced(self):
        tool_content = json.dumps({"source_number": 1, "content": "Single"})
        original_content = "See [source1]."
        assert _trim_tool_content_to_used_sources(original_content, tool_content) == tool_content

    def test_single_object_dropped_when_not_referenced(self):
        tool_content = json.dumps({"source_number": 0, "content": "Single"})
        original_content = "See [source1]."
        assert (
            _trim_tool_content_to_used_sources(original_content, tool_content)
            == "No relevant sources found."
        )

    def test_handles_source_number_as_string_in_json(self):
        tool_content = json.dumps(
            [{"source_number": "0", "content": "A"}, {"source_number": "1", "content": "B"}]
        )
        original_content = " [source0] "
        result = _trim_tool_content_to_used_sources(original_content, tool_content)
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["content"] == "A"

    def test_returns_unchanged_on_invalid_json(self):
        tool_content = "not valid json [source0]"
        original_content = " [source0] "
        assert _trim_tool_content_to_used_sources(original_content, tool_content) == tool_content


class TestAppendLastToolCallsAndToolMessage:
    """Tests for _append_last_tool_calls_and_tool_message (idempotency and trimming)."""

    def test_appends_only_last_assistant_and_last_tool_message(self):
        gpt_request = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Search."},
            {
                "role": "assistant",
                "content": "First call",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "Search", "arguments": '{"q": "a"}'},
                    }
                ],
            },
            {"role": "tool", "name": "Search", "tool_call_id": "call_1", "content": "First result"},
            {
                "role": "assistant",
                "content": "Second call",
                "tool_calls": [
                    {
                        "id": "call_2",
                        "function": {"name": "Search", "arguments": '{"q": "b"}'},
                    }
                ],
            },
            {"role": "tool", "name": "Search", "tool_call_id": "call_2", "content": "Second result"},
        ]
        builder = LanguageModelMessages([]).builder()
        _append_last_tool_calls_and_tool_message(builder, gpt_request)
        messages = builder.build()
        assert len(messages.root) == 2
        assert messages.root[0].role == "assistant"
        assert messages.root[0].content == "Second call"
        assert messages.root[1].role == "tool"
        assert messages.root[1].content == "Second result"

    def test_tool_content_trimmed_using_original_content_from_next(self):
        gpt_request = [
            {"role": "user", "content": "Search."},
            {
                "role": "assistant",
                "content": "Call",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "Search", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "name": "Search",
                "tool_call_id": "call_1",
                "content": json.dumps(
                    [
                        {"source_number": 0, "content": "A"},
                        {"source_number": 1, "content": "B"},
                        {"source_number": 2, "content": "C"},
                    ]
                ),
            },
        ]
        builder = LanguageModelMessages([]).builder()
        original_content_from_next = "Answer uses [source0] and [source2]."
        _append_last_tool_calls_and_tool_message(
            builder,
            gpt_request,
            original_content_from_next=original_content_from_next,
        )
        messages = builder.build()
        assert len(messages.root) == 2
        tool_content = json.loads(messages.root[1].content)
        assert len(tool_content) == 2
        assert tool_content[0]["source_number"] == 0
        assert tool_content[1]["source_number"] == 2

    def test_appends_nothing_when_no_tool_calls_or_tool_message(self):
        gpt_request = [
            {"role": "user", "content": "Hello"},
        ]
        builder = LanguageModelMessages([]).builder()
        _append_last_tool_calls_and_tool_message(builder, gpt_request)
        messages = builder.build()
        assert len(messages.root) == 0

    def test_appends_only_assistant_when_no_tool_message(self):
        gpt_request = [
            {
                "role": "assistant",
                "content": "Call",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {"name": "Search", "arguments": "{}"},
                    }
                ],
            },
        ]
        builder = LanguageModelMessages([]).builder()
        _append_last_tool_calls_and_tool_message(builder, gpt_request)
        messages = builder.build()
        assert len(messages.root) == 1
        assert messages.root[0].role == "assistant"
        assert messages.root[0].content == "Call"

    def test_appends_only_tool_message_when_no_assistant_with_tool_calls(self):
        gpt_request = [
            {"role": "tool", "name": "X", "tool_call_id": "id", "content": "result"},
        ]
        builder = LanguageModelMessages([]).builder()
        _append_last_tool_calls_and_tool_message(builder, gpt_request)
        messages = builder.build()
        assert len(messages.root) == 1
        assert messages.root[0].role == "tool"
        assert messages.root[0].content == "result"
