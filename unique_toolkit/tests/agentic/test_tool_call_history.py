import json
from unittest.mock import MagicMock, patch

from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    _convert_raw_messages_to_typed,
    _extract_tool_messages_per_turn,
    _interleave_tool_messages,
    _parse_source_items,
    _segment_gpt_request_into_turns,
    _strip_uncited_sources,
    get_full_history_with_contents_and_tool_calls,
)
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.language_model import LanguageModelMessageRole as LLMRole
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessage,
    LanguageModelMessages,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)

# ---------------------------------------------------------------------------
# _parse_source_items
# ---------------------------------------------------------------------------


class TestParseSourceItems:
    def test_list_of_sources(self):
        content = json.dumps(
            [{"source_number": 1, "text": "a"}, {"source_number": 2, "text": "b"}]
        )
        items, was_single = _parse_source_items(content)
        assert items is not None
        assert len(items) == 2
        assert not was_single

    def test_single_source_dict(self):
        content = json.dumps({"source_number": 5, "text": "x"})
        items, was_single = _parse_source_items(content)
        assert items == [{"source_number": 5, "text": "x"}]
        assert was_single

    def test_invalid_json(self):
        items, was_single = _parse_source_items("not json")
        assert items is None
        assert not was_single

    def test_empty_list(self):
        items, was_single = _parse_source_items("[]")
        assert items is None

    def test_list_without_source_number(self):
        content = json.dumps([{"title": "no source_number"}])
        items, was_single = _parse_source_items(content)
        assert items is None

    def test_dict_without_source_number(self):
        content = json.dumps({"title": "no source_number"})
        items, was_single = _parse_source_items(content)
        assert items is None


# ---------------------------------------------------------------------------
# _strip_uncited_sources
# ---------------------------------------------------------------------------


class TestStripUncitedSources:
    def test_strips_uncited(self):
        tool_content = json.dumps(
            [
                {"source_number": 1, "text": "cited"},
                {"source_number": 2, "text": "uncited"},
                {"source_number": 3, "text": "cited too"},
            ]
        )
        messages = LanguageModelMessages(
            root=[
                LanguageModelToolMessage(
                    content=tool_content, tool_call_id="c1", name="WebSearch"
                ),
                LanguageModelAssistantMessage(content="See [source1] and [source3]."),
            ]
        )
        result = _strip_uncited_sources(messages)
        tool_msg = result.root[0]
        items = json.loads(tool_msg.content)
        source_numbers = {it["source_number"] for it in items}
        assert source_numbers == {1, 3}

    def test_no_assistant_strips_all(self):
        tool_content = json.dumps([{"source_number": 1, "text": "a"}])
        messages = LanguageModelMessages(
            root=[
                LanguageModelToolMessage(
                    content=tool_content, tool_call_id="c1", name="t"
                )
            ]
        )
        result = _strip_uncited_sources(messages)
        items = json.loads(result.root[0].content)
        assert items == []

    def test_non_source_tool_message_unchanged(self):
        messages = LanguageModelMessages(
            root=[
                LanguageModelToolMessage(
                    content="plain text", tool_call_id="c1", name="t"
                )
            ]
        )
        result = _strip_uncited_sources(messages)
        assert result.root[0].content == "plain text"


# ---------------------------------------------------------------------------
# _segment_gpt_request_into_turns
# ---------------------------------------------------------------------------


class TestSegmentGptRequest:
    def test_single_turn(self):
        gpt = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        turns = _segment_gpt_request_into_turns(gpt)
        assert len(turns) == 1
        assert turns[0][0]["role"] == "user"

    def test_multi_turn(self):
        gpt = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
        ]
        turns = _segment_gpt_request_into_turns(gpt)
        assert len(turns) == 2
        assert turns[0][0]["content"] == "q1"
        assert turns[1][0]["content"] == "q2"

    def test_empty(self):
        assert _segment_gpt_request_into_turns([]) == []

    def test_system_only(self):
        assert (
            _segment_gpt_request_into_turns([{"role": "system", "content": "s"}]) == []
        )


# ---------------------------------------------------------------------------
# _extract_tool_messages_per_turn
# ---------------------------------------------------------------------------


class TestExtractToolMessagesPerTurn:
    def test_single_turn_includes_everything_after_user(self):
        """Single turn is the last turn, so everything after user is included."""
        gpt = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "search"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1"}]},
            {"role": "tool", "content": "result", "tool_call_id": "c1"},
            {"role": "assistant", "content": "final answer"},
        ]
        result = _extract_tool_messages_per_turn(gpt)
        assert len(result) == 1
        assert len(result[0]) == 3
        assert result[0][0]["role"] == "assistant"
        assert result[0][1]["role"] == "tool"
        assert result[0][2]["role"] == "assistant"

    def test_non_last_turn_excludes_final_assistant(self):
        """Non-last turns strip the concluding assistant message."""
        gpt = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1"}]},
            {"role": "tool", "content": "result", "tool_call_id": "c1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
        ]
        result = _extract_tool_messages_per_turn(gpt)
        assert len(result) == 2
        assert len(result[0]) == 2
        assert result[0][0]["role"] == "assistant"
        assert result[0][1]["role"] == "tool"

    def test_last_turn_includes_all_after_user(self):
        gpt = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1"}]},
            {"role": "tool", "content": "result", "tool_call_id": "c1"},
        ]
        result = _extract_tool_messages_per_turn(gpt)
        assert len(result) == 2
        assert len(result[1]) == 2

    def test_single_turn_without_tool_calls(self):
        """Last turn includes the assistant message (no stripping for last turn)."""
        gpt = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        result = _extract_tool_messages_per_turn(gpt)
        assert len(result) == 1
        assert len(result[0]) == 1
        assert result[0][0]["content"] == "hello"


# ---------------------------------------------------------------------------
# _convert_raw_messages_to_typed
# ---------------------------------------------------------------------------


class TestConvertRawMessages:
    def test_assistant_with_tool_calls(self):
        raw = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "WebSearch", "arguments": "{}"},
                    }
                ],
            }
        ]
        result = _convert_raw_messages_to_typed(raw)
        assert len(result) == 1
        assert result[0].role == LLMRole.ASSISTANT
        assert result[0].tool_calls is not None

    def test_tool_message(self):
        raw = [
            {
                "role": "tool",
                "content": "data",
                "tool_call_id": "c1",
                "name": "WebSearch",
            }
        ]
        result = _convert_raw_messages_to_typed(raw)
        assert len(result) == 1
        assert result[0].role == LLMRole.TOOL
        assert result[0].content == "data"

    def test_user_message_fallback(self):
        raw = [{"role": "user", "content": "hi"}]
        result = _convert_raw_messages_to_typed(raw)
        assert len(result) == 1
        assert result[0].role == LLMRole.USER

    def test_malformed_message_skipped(self):
        raw = [{"role": "invalid_role_xyz", "content": "bad"}]
        result = _convert_raw_messages_to_typed(raw)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# _interleave_tool_messages
# ---------------------------------------------------------------------------


class TestInterleaveToolMessages:
    def test_inserts_after_user(self):
        enriched = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="q1"),
                LanguageModelMessage(role=LLMRole.ASSISTANT, content="a1"),
                LanguageModelUserMessage(content="q2"),
                LanguageModelMessage(role=LLMRole.ASSISTANT, content="a2"),
            ]
        )
        tool_msgs = [
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "T", "arguments": "{}"},
                        }
                    ],
                },
                {"role": "tool", "content": "res1", "tool_call_id": "c1", "name": "T"},
            ],
            [],
        ]
        result = _interleave_tool_messages(enriched, tool_msgs)
        roles = [m.role for m in result.root]
        assert roles == [
            LLMRole.USER,
            LLMRole.ASSISTANT,
            LLMRole.TOOL,
            LLMRole.ASSISTANT,
            LLMRole.USER,
            LLMRole.ASSISTANT,
        ]

    def test_no_tool_messages(self):
        enriched = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="q"),
                LanguageModelMessage(role=LLMRole.ASSISTANT, content="a"),
            ]
        )
        result = _interleave_tool_messages(enriched, [[]])
        assert len(result.root) == 2

    def test_more_turns_than_tool_groups(self):
        enriched = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="q1"),
                LanguageModelMessage(role=LLMRole.ASSISTANT, content="a1"),
                LanguageModelUserMessage(content="q2"),
                LanguageModelMessage(role=LLMRole.ASSISTANT, content="a2"),
            ]
        )
        result = _interleave_tool_messages(enriched, [[]])
        assert len(result.root) == 4


# ---------------------------------------------------------------------------
# get_full_history_with_contents_and_tool_calls (integration)
# ---------------------------------------------------------------------------

MODULE = "unique_toolkit.agentic.history_manager.history_construction_with_contents"


def _make_user_message():
    return MagicMock(
        id="msg-1",
        text="hello",
        original_text="hello",
        created_at="2026-01-01T00:00:00Z",
        language="en",
    )


def _make_enriched_history():
    return LanguageModelMessages(
        root=[
            LanguageModelUserMessage(content="hello"),
            LanguageModelMessage(role=LLMRole.ASSISTANT, content="hi there"),
        ]
    )


class TestGetFullHistoryWithContentsAndToolCalls:
    @patch(f"{MODULE}.get_full_history_with_contents")
    def test_no_gpt_request_returns_enriched(self, mock_get_full):
        enriched = _make_enriched_history()
        mock_get_full.return_value = enriched

        chat_service = MagicMock()
        chat_service.get_full_history.return_value = [
            ChatMessage(
                chat_id="c1", role=ChatMessageRole.USER, text="hello", gpt_request=None
            ),
        ]

        result = get_full_history_with_contents_and_tool_calls(
            user_message=_make_user_message(),
            chat_id="c1",
            chat_service=chat_service,
            content_service=MagicMock(),
        )
        assert result == enriched

    @patch(f"{MODULE}.get_full_history_with_contents")
    def test_no_gpt_request_with_token_limit(self, mock_get_full):
        enriched = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="a " * 200),
                LanguageModelMessage(role=LLMRole.ASSISTANT, content="b " * 200),
            ]
        )
        mock_get_full.return_value = enriched

        chat_service = MagicMock()
        chat_service.get_full_history.return_value = [
            ChatMessage(
                chat_id="c1", role=ChatMessageRole.USER, text="hello", gpt_request=None
            ),
        ]

        result = get_full_history_with_contents_and_tool_calls(
            user_message=_make_user_message(),
            chat_id="c1",
            chat_service=chat_service,
            content_service=MagicMock(),
            token_limit=50,
        )
        assert len(result.root) < len(enriched.root)

    @patch(f"{MODULE}.get_full_history_with_contents")
    def test_with_gpt_request_interleaves_and_strips(self, mock_get_full):
        tool_content = json.dumps(
            [
                {"source_number": 1, "text": "cited src"},
                {"source_number": 2, "text": "uncited src"},
            ]
        )
        gpt_request = [
            {"role": "user", "content": "search web"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "WebSearch", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "content": tool_content,
                "tool_call_id": "c1",
                "name": "WebSearch",
            },
        ]
        enriched = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="search web"),
                LanguageModelMessage(
                    role=LLMRole.ASSISTANT, content="See [source1] for info."
                ),
            ]
        )
        mock_get_full.return_value = enriched

        chat_service = MagicMock()
        chat_service.get_full_history.return_value = [
            ChatMessage(
                chat_id="c1",
                role=ChatMessageRole.USER,
                text="search web",
                gpt_request=gpt_request,
            ),
        ]

        result = get_full_history_with_contents_and_tool_calls(
            user_message=_make_user_message(),
            chat_id="c1",
            chat_service=chat_service,
            content_service=MagicMock(),
        )

        roles = [m.role for m in result.root]
        assert LLMRole.TOOL in roles

        tool_msgs = [m for m in result.root if m.role == LLMRole.TOOL]
        assert len(tool_msgs) == 1
        items = json.loads(tool_msgs[0].content)
        assert len(items) == 1
        assert items[0]["source_number"] == 1

    @patch(f"{MODULE}.get_full_history_with_contents")
    def test_with_gpt_request_and_token_limit(self, mock_get_full):
        gpt_request = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        enriched = LanguageModelMessages(
            root=[
                LanguageModelUserMessage(content="a " * 200),
                LanguageModelMessage(role=LLMRole.ASSISTANT, content="b " * 200),
            ]
        )
        mock_get_full.return_value = enriched

        chat_service = MagicMock()
        chat_service.get_full_history.return_value = [
            ChatMessage(
                chat_id="c1",
                role=ChatMessageRole.USER,
                text="hi",
                gpt_request=gpt_request,
            ),
        ]

        result = get_full_history_with_contents_and_tool_calls(
            user_message=_make_user_message(),
            chat_id="c1",
            chat_service=chat_service,
            content_service=MagicMock(),
            token_limit=50,
        )
        assert len(result.root) <= len(enriched.root) + 1
