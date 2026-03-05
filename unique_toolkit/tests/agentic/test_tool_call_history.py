import json
from collections import defaultdict
from datetime import datetime
from unittest.mock import MagicMock, patch

from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    get_full_history_with_contents_and_tool_calls,
)
from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.chat.schemas import (
    ChatMessage,
    ChatMessageRole,
    ToolCallRecord,
    ToolResponseRecord,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelFunctionCall,
    LanguageModelMessages,
    LanguageModelToolMessage,
)


class TestExtractToolCallRecords:
    def _make_history_manager(self) -> HistoryManager:
        hm = HistoryManager.__new__(HistoryManager)
        hm._loop_history = []
        return hm

    def test_empty_history(self):
        hm = self._make_history_manager()
        assert hm.extract_tool_call_records() == []

    def test_single_round_single_tool(self):
        hm = self._make_history_manager()
        fn = LanguageModelFunction(id="call_1", name="search", arguments={"q": "test"})
        hm._loop_history = [
            LanguageModelAssistantMessage.from_functions(tool_calls=[fn]),
            LanguageModelToolMessage(
                tool_call_id="call_1", content="result", name="search"
            ),
        ]
        records = hm.extract_tool_call_records()
        assert len(records) == 1
        assert records[0].external_tool_call_id == "call_1"
        assert records[0].function_name == "search"
        assert records[0].arguments == {"q": "test"}
        assert records[0].round_index == 0
        assert records[0].sequence_index == 0
        assert records[0].response is not None
        assert records[0].response.content == "result"

    def test_single_round_parallel_tools(self):
        hm = self._make_history_manager()
        fn_a = LanguageModelFunction(id="call_a", name="search", arguments={"q": "a"})
        fn_b = LanguageModelFunction(id="call_b", name="calc", arguments={"x": 1})
        hm._loop_history = [
            LanguageModelAssistantMessage.from_functions(tool_calls=[fn_a, fn_b]),
            LanguageModelToolMessage(tool_call_id="call_a", content="res_a", name="search"),
            LanguageModelToolMessage(tool_call_id="call_b", content="res_b", name="calc"),
        ]
        records = hm.extract_tool_call_records()
        assert len(records) == 2
        assert records[0].sequence_index == 0
        assert records[1].sequence_index == 1
        assert records[0].round_index == records[1].round_index == 0

    def test_multiple_rounds(self):
        hm = self._make_history_manager()
        fn1 = LanguageModelFunction(id="c1", name="t1", arguments=None)
        fn2 = LanguageModelFunction(id="c2", name="t2", arguments=None)
        hm._loop_history = [
            LanguageModelAssistantMessage.from_functions(tool_calls=[fn1]),
            LanguageModelToolMessage(tool_call_id="c1", content="r1", name="t1"),
            LanguageModelAssistantMessage.from_functions(tool_calls=[fn2]),
            LanguageModelToolMessage(tool_call_id="c2", content="r2", name="t2"),
        ]
        records = hm.extract_tool_call_records()
        assert len(records) == 2
        assert records[0].round_index == 0
        assert records[1].round_index == 1

    def test_missing_response(self):
        hm = self._make_history_manager()
        fn = LanguageModelFunction(id="c1", name="t1", arguments=None)
        hm._loop_history = [
            LanguageModelAssistantMessage.from_functions(tool_calls=[fn]),
        ]
        records = hm.extract_tool_call_records()
        assert len(records) == 1
        assert records[0].response is None

    def test_none_id_becomes_empty_string(self):
        hm = self._make_history_manager()
        tc = LanguageModelFunctionCall(
            id=None,
            type="function",
            function=LanguageModelFunction(name="t1", arguments=None),
        )
        assistant_msg = LanguageModelAssistantMessage(content="", tool_calls=[tc])
        hm._loop_history = [assistant_msg]
        records = hm.extract_tool_call_records()
        assert len(records) == 1
        assert records[0].external_tool_call_id == ""


class TestGetFullHistoryWithContentsAndToolCalls:
    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_chat_history_with_contents"
    )
    def test_interleaves_tool_calls_from_db(self, mock_get_contents):
        mock_chat_service = MagicMock()
        mock_content_service = MagicMock()
        mock_content_service.search_contents.return_value = []

        user_msg = MagicMock()
        user_msg.id = "msg3"
        user_msg.text = "follow up"
        user_msg.original_text = "follow up"
        user_msg.created_at = "2026-01-01T00:00:02"

        mock_chat_service.get_full_history.return_value = [
            ChatMessage(
                id="msg1",
                chat_id="chat1",
                role=ChatMessageRole.USER,
                text="hello",
                created_at=datetime(2026, 1, 1, 0, 0, 0),
            ),
            ChatMessage(
                id="msg2",
                chat_id="chat1",
                role=ChatMessageRole.ASSISTANT,
                text="The answer is 4.",
                created_at=datetime(2026, 1, 1, 0, 0, 1),
            ),
        ]

        tool_call_records = [
            ToolCallRecord(
                external_tool_call_id="tc1",
                function_name="calculator",
                arguments={"expr": "2+2"},
                round_index=0,
                sequence_index=0,
                message_id="msg2",
                response=ToolResponseRecord(content="4"),
            ),
        ]
        mock_chat_service.list_tool_calls_by_message_ids.return_value = tool_call_records

        from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
            ChatHistoryWithContent,
            ChatMessageWithContents,
        )

        mock_get_contents.return_value = ChatHistoryWithContent(
            root=[
                ChatMessageWithContents(
                    chat_id="chat1",
                    role=ChatMessageRole.USER,
                    text="hello",
                    originalText="hello",
                    created_at=datetime(2026, 1, 1, 0, 0, 0),
                ),
                ChatMessageWithContents(
                    id="msg2",
                    chat_id="chat1",
                    role=ChatMessageRole.ASSISTANT,
                    text="The answer is 4.",
                    originalText="The answer is 4.",
                    created_at=datetime(2026, 1, 1, 0, 0, 1),
                ),
                ChatMessageWithContents(
                    chat_id="chat1",
                    role=ChatMessageRole.USER,
                    text="follow up",
                    originalText="follow up",
                    created_at=datetime(2026, 1, 1, 0, 0, 2),
                ),
            ]
        )

        result = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        assert isinstance(result, LanguageModelMessages)
        # user -> assistant_with_tool_calls -> tool_response -> assistant_final -> user
        assert len(result.root) == 5
        assert result.root[0].role.value == "user"
        assert isinstance(result.root[1], LanguageModelAssistantMessage)
        assert result.root[1].tool_calls is not None
        assert result.root[1].tool_calls[0].function.name == "calculator"
        assert isinstance(result.root[2], LanguageModelToolMessage)
        assert result.root[2].content == "4"
        assert result.root[3].role.value == "assistant"
        assert result.root[4].role.value == "user"

    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_chat_history_with_contents"
    )
    def test_user_only_history(self, mock_get_contents):
        mock_chat_service = MagicMock()
        mock_content_service = MagicMock()
        mock_content_service.search_contents.return_value = []

        user_msg = MagicMock()
        user_msg.id = "um1"
        user_msg.text = "Hello"
        user_msg.original_text = "Hello"
        user_msg.created_at = "2026-01-01T00:00:00"

        mock_chat_service.get_full_history.return_value = []
        mock_chat_service.list_tool_calls_by_message_ids.return_value = []

        from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
            ChatHistoryWithContent,
            ChatMessageWithContents,
        )

        mock_get_contents.return_value = ChatHistoryWithContent(
            root=[
                ChatMessageWithContents(
                    chat_id="chat1",
                    role=ChatMessageRole.USER,
                    text="Hello",
                    originalText="Hello",
                    created_at=datetime(2026, 1, 1, 0, 0, 0),
                ),
            ]
        )

        result = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        assert isinstance(result, LanguageModelMessages)
        assert len(result.root) == 1
        assert result.root[0].role.value == "user"


class TestCompactToolCallRecords:
    def _make_sources(self, source_numbers: list[int]) -> str:
        return json.dumps(
            [{"source_number": n, "content": f"content for {n}"} for n in source_numbers]
        )

    def _make_record(self, response_content: str | None = None) -> ToolCallRecord:
        return ToolCallRecord(
            external_tool_call_id="call_1",
            function_name="search",
            arguments={"q": "test"},
            round_index=0,
            sequence_index=0,
            response=ToolResponseRecord(content=response_content) if response_content is not None else None,
        )

    def test_no_assistant_text_returns_records_unchanged(self):
        content = self._make_sources([0, 1, 2])
        records = [self._make_record(content)]
        result = HistoryManager.compact_tool_call_records(records, None)
        assert result[0].response.content == content

    def test_empty_assistant_text_returns_records_unchanged(self):
        content = self._make_sources([0, 1, 2])
        records = [self._make_record(content)]
        result = HistoryManager.compact_tool_call_records(records, "")
        assert result[0].response.content == content

    def test_no_citations_returns_records_unchanged(self):
        content = self._make_sources([0, 1, 2])
        records = [self._make_record(content)]
        result = HistoryManager.compact_tool_call_records(records, "No sources used here.")
        assert result[0].response.content == content

    def test_strips_uncited_sources(self):
        content = self._make_sources([0, 1, 2, 3, 4])
        records = [self._make_record(content)]
        result = HistoryManager.compact_tool_call_records(
            records, "The answer is sunny [source0] and warm [source3]."
        )
        parsed = json.loads(result[0].response.content)
        assert len(parsed) == 2
        assert {item["source_number"] for item in parsed} == {0, 3}

    def test_keeps_all_when_all_cited(self):
        content = self._make_sources([5, 6])
        records = [self._make_record(content)]
        result = HistoryManager.compact_tool_call_records(
            records, "Info from [source5] and [source6]."
        )
        parsed = json.loads(result[0].response.content)
        assert len(parsed) == 2

    def test_non_json_content_left_unchanged(self):
        records = [self._make_record("plain text result")]
        result = HistoryManager.compact_tool_call_records(
            records, "Used [source0] here."
        )
        assert result[0].response.content == "plain text result"

    def test_no_response_record_is_safe(self):
        records = [self._make_record(None)]
        records[0].response = None
        result = HistoryManager.compact_tool_call_records(
            records, "Used [source0] here."
        )
        assert result[0].response is None

    def test_multiple_records_compacted_independently(self):
        r1 = self._make_record(self._make_sources([0, 1, 2]))
        r2 = ToolCallRecord(
            external_tool_call_id="call_2",
            function_name="web_search",
            arguments={"q": "weather"},
            round_index=1,
            sequence_index=0,
            response=ToolResponseRecord(content=self._make_sources([3, 4, 5])),
        )
        result = HistoryManager.compact_tool_call_records(
            [r1, r2], "From [source1] and [source4] we know..."
        )
        parsed_r1 = json.loads(result[0].response.content)
        parsed_r2 = json.loads(result[1].response.content)
        assert len(parsed_r1) == 1
        assert parsed_r1[0]["source_number"] == 1
        assert len(parsed_r2) == 1
        assert parsed_r2[0]["source_number"] == 4

    def test_case_insensitive_citation_matching(self):
        content = self._make_sources([0, 1])
        records = [self._make_record(content)]
        result = HistoryManager.compact_tool_call_records(
            records, "Per [Source0] this is correct."
        )
        parsed = json.loads(result[0].response.content)
        assert len(parsed) == 1
        assert parsed[0]["source_number"] == 0
