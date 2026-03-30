import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    get_full_history_with_contents_and_tool_calls,
)
from unique_toolkit.agentic.history_manager.history_manager import HistoryManager
from unique_toolkit.chat.schemas import (
    ChatMessage,
    ChatMessageRole,
    ChatMessageTool,
    ChatMessageToolResponse,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelFunctionCall,
    LanguageModelMessages,
    LanguageModelToolMessage,
)


class TestExtractMessageTools:
    def _make_history_manager(self) -> HistoryManager:
        hm = HistoryManager.__new__(HistoryManager)
        hm._loop_history = []
        return hm

    @pytest.mark.ai
    def test_empty_history(self):
        """
        Purpose: Verify that extract_message_tools returns an empty list when
            the loop history contains no messages.
        Why this matters: Callers may invoke this on a fresh loop; returning []
            instead of raising prevents spurious persistence calls.
        Setup summary: HistoryManager with empty _loop_history → expect [].
        """
        hm = self._make_history_manager()
        assert hm.extract_message_tools() == []

    @pytest.mark.ai
    def test_single_round_single_tool(self):
        """
        Purpose: A single assistant message with one tool call and one response is
            extracted as a single ChatMessageTool record with correct fields.
        Why this matters: The resulting record is persisted to the DB; any missing
            or wrong field (name, arguments, response) breaks retrieval and re-play.
        Setup summary: One assistant message with tool_call "search", one tool
            response with content "result" → one record with matching fields.
        """
        hm = self._make_history_manager()
        fn = LanguageModelFunction(id="call_1", name="search", arguments={"q": "test"})
        hm._loop_history = [
            LanguageModelAssistantMessage.from_functions(tool_calls=[fn]),
            LanguageModelToolMessage(
                tool_call_id="call_1", content="result", name="search"
            ),
        ]
        records = hm.extract_message_tools()
        assert len(records) == 1
        assert records[0].external_tool_call_id == "call_1"
        assert records[0].function_name == "search"
        assert records[0].arguments == {"q": "test"}
        assert records[0].round_index == 0
        assert records[0].sequence_index == 0
        assert records[0].response is not None
        assert records[0].response.content == "result"

    @pytest.mark.ai
    def test_single_round_parallel_tools(self):
        """
        Purpose: Two tool calls in the same assistant message are extracted as two
            records with sequence_index 0 and 1 sharing the same round_index.
        Why this matters: Parallel tool calls must be stored with correct ordering
            metadata so they can be reconstructed as a single grouped assistant
            message on history reload.
        Setup summary: One assistant message with two functions; two tool responses
            → two records with round_index=0 and sequence_index 0, 1.
        """
        hm = self._make_history_manager()
        fn_a = LanguageModelFunction(id="call_a", name="search", arguments={"q": "a"})
        fn_b = LanguageModelFunction(id="call_b", name="calc", arguments={"x": 1})
        hm._loop_history = [
            LanguageModelAssistantMessage.from_functions(tool_calls=[fn_a, fn_b]),
            LanguageModelToolMessage(
                tool_call_id="call_a", content="res_a", name="search"
            ),
            LanguageModelToolMessage(
                tool_call_id="call_b", content="res_b", name="calc"
            ),
        ]
        records = hm.extract_message_tools()
        assert len(records) == 2
        assert records[0].sequence_index == 0
        assert records[1].sequence_index == 1
        assert records[0].round_index == records[1].round_index == 0

    @pytest.mark.ai
    def test_multiple_rounds(self):
        """
        Purpose: Tool calls across two separate agentic rounds are extracted with
            incrementing round_index values.
        Why this matters: round_index is the primary ordering key for multi-round
            reconstruction; if it is wrong, tool calls replay out of order and the
            reconstructed conversation is invalid.
        Setup summary: Two assistant+tool pairs → two records with round_index 0, 1.
        """
        hm = self._make_history_manager()
        fn1 = LanguageModelFunction(id="c1", name="t1", arguments=None)
        fn2 = LanguageModelFunction(id="c2", name="t2", arguments=None)
        hm._loop_history = [
            LanguageModelAssistantMessage.from_functions(tool_calls=[fn1]),
            LanguageModelToolMessage(tool_call_id="c1", content="r1", name="t1"),
            LanguageModelAssistantMessage.from_functions(tool_calls=[fn2]),
            LanguageModelToolMessage(tool_call_id="c2", content="r2", name="t2"),
        ]
        records = hm.extract_message_tools()
        assert len(records) == 2
        assert records[0].round_index == 0
        assert records[1].round_index == 1

    @pytest.mark.ai
    def test_missing_response(self):
        """
        Purpose: A tool call with no matching response message produces a record
            with response=None rather than being silently dropped.
        Why this matters: Dropping the record would lose evidence of the call,
            making debugging harder; response=None is the explicit "no result" sentinel.
        Setup summary: Assistant message with one tool call, no subsequent tool
            message → one record with response is None.
        """
        hm = self._make_history_manager()
        fn = LanguageModelFunction(id="c1", name="t1", arguments=None)
        hm._loop_history = [
            LanguageModelAssistantMessage.from_functions(tool_calls=[fn]),
        ]
        records = hm.extract_message_tools()
        assert len(records) == 1
        assert records[0].response is None

    @pytest.mark.ai
    def test_none_id_becomes_empty_string(self):
        """
        Purpose: A tool call whose id is None is stored with external_tool_call_id=""
            instead of None.
        Why this matters: external_tool_call_id is a non-nullable DB column; a None
            value would raise an integrity error on persistence.
        Setup summary: LanguageModelFunctionCall with id=None → record has
            external_tool_call_id == "".
        """
        hm = self._make_history_manager()
        tc = LanguageModelFunctionCall(
            id=None,
            type="function",
            function=LanguageModelFunction(name="t1", arguments=None),
        )
        assistant_msg = LanguageModelAssistantMessage(content="", tool_calls=[tc])
        hm._loop_history = [assistant_msg]
        records = hm.extract_message_tools()
        assert len(records) == 1
        assert records[0].external_tool_call_id == ""


class TestGetFullHistoryWithContentsAndToolCalls:
    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_chat_history_with_contents"
    )
    @pytest.mark.ai
    def test_interleaves_tool_calls_from_db(self, mock_get_contents):
        """
        Purpose: Persisted tool call records are interleaved with the assistant message
            they belong to, producing the correct OpenAI message sequence.
        Why this matters: The LLM requires the sequence
            assistant(tool_calls) → tool → assistant(final_text); any deviation
            causes a 400 error from the model API.
        Setup summary: One assistant DB message with one persisted tool call record
            → reconstructed history has 5 messages in the correct order.
        """
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
            ChatMessageTool(
                external_tool_call_id="tc1",
                function_name="calculator",
                arguments={"expr": "2+2"},
                round_index=0,
                sequence_index=0,
                message_id="msg2",
                response=ChatMessageToolResponse(content="4"),
            ),
        ]
        mock_chat_service.get_message_tools.return_value = tool_call_records

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

        result, _, _ = get_full_history_with_contents_and_tool_calls(
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

    def _make_history_context(
        self,
        assistant_messages: list[tuple[str, str]],
        tool_call_records: list[ChatMessageTool],
        user_follow_up: str = "follow up",
    ):
        """Build the standard mock objects for get_full_history_with_contents_and_tool_calls."""
        from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
            ChatHistoryWithContent,
            ChatMessageWithContents,
        )

        mock_chat_service = MagicMock()
        mock_content_service = MagicMock()
        mock_content_service.search_contents.return_value = []

        user_msg = MagicMock()
        user_msg.id = "user_followup"
        user_msg.text = user_follow_up
        user_msg.original_text = user_follow_up
        user_msg.created_at = "2026-01-01T00:01:00"

        history_messages = []
        content_messages = []
        for idx, (msg_id, text) in enumerate(assistant_messages):
            dt = datetime(2026, 1, 1, 0, 0, idx)
            history_messages.append(
                ChatMessage(
                    id=msg_id,
                    chat_id="chat1",
                    role=ChatMessageRole.ASSISTANT,
                    text=text,
                    created_at=dt,
                )
            )
            content_messages.append(
                ChatMessageWithContents(
                    id=msg_id,
                    chat_id="chat1",
                    role=ChatMessageRole.ASSISTANT,
                    text=text,
                    originalText=text,
                    created_at=dt,
                )
            )

        mock_chat_service.get_full_history.return_value = history_messages
        mock_chat_service.get_message_tools.return_value = tool_call_records

        content_messages.append(
            ChatMessageWithContents(
                chat_id="chat1",
                role=ChatMessageRole.USER,
                text=user_follow_up,
                originalText=user_follow_up,
                created_at=datetime(2026, 1, 1, 0, 1, 0),
            )
        )
        mock_get_contents = ChatHistoryWithContent(root=content_messages)
        return mock_chat_service, mock_content_service, user_msg, mock_get_contents

    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_chat_history_with_contents"
    )
    @pytest.mark.ai
    def test_parallel_tool_calls_grouped_into_single_assistant_message(
        self, mock_get_contents
    ):
        """
        Purpose: Two tool calls with the same round_index are emitted as a single
            assistant message carrying both tool_calls, followed by two separate
            tool response messages.
        Why this matters: OpenAI requires that all parallel tool calls in one round
            appear in a single assistant message; splitting them causes API errors.
        Setup summary: One DB assistant message with two tool records (round_index=0,
            sequence_index 0 and 1) → assistant message with 2 tool_calls, then 2
            tool messages, then final assistant and user.
        """
        mock_chat_service, mock_content_service, user_msg, history = (
            self._make_history_context(
                assistant_messages=[("msg1", "Used two tools in parallel.")],
                tool_call_records=[
                    ChatMessageTool(
                        external_tool_call_id="tc_a",
                        function_name="search",
                        arguments={"q": "a"},
                        round_index=0,
                        sequence_index=0,
                        message_id="msg1",
                        response=ChatMessageToolResponse(content="res_a"),
                    ),
                    ChatMessageTool(
                        external_tool_call_id="tc_b",
                        function_name="calc",
                        arguments={"x": 1},
                        round_index=0,
                        sequence_index=1,
                        message_id="msg1",
                        response=ChatMessageToolResponse(content="res_b"),
                    ),
                ],
            )
        )
        mock_get_contents.return_value = history

        result, _, _ = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        # Expected: assistant(2 tool_calls) -> tool_msg_a -> tool_msg_b -> assistant_final -> user
        messages = result.root
        assert len(messages) == 5
        assert isinstance(messages[0], LanguageModelAssistantMessage)
        assert messages[0].tool_calls is not None
        assert len(messages[0].tool_calls) == 2
        assert {tc.function.name for tc in messages[0].tool_calls} == {"search", "calc"}
        assert isinstance(messages[1], LanguageModelToolMessage)
        assert isinstance(messages[2], LanguageModelToolMessage)
        assert {messages[1].content, messages[2].content} == {"res_a", "res_b"}
        assert messages[3].role.value == "assistant"
        assert messages[4].role.value == "user"

    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_chat_history_with_contents"
    )
    @pytest.mark.ai
    def test_multi_round_tool_calls_interleaved_in_order(self, mock_get_contents):
        """
        Purpose: Tool calls from two distinct rounds (round_index 0 and 1) produce
            two separate assistant+tool pairs interleaved in chronological order.
        Why this matters: Multi-round tool use is a core agentic pattern; wrong
            ordering corrupts the conversation context fed to the LLM on the next turn.
        Setup summary: Two tool records with round_index 0 and 1 attached to the
            same DB message → 6-message sequence:
            asst(tc1) → tool(r1) → asst(tc2) → tool(r2) → asst_final → user.
        """
        mock_chat_service, mock_content_service, user_msg, history = (
            self._make_history_context(
                assistant_messages=[("msg1", "Two rounds of tool calls.")],
                tool_call_records=[
                    ChatMessageTool(
                        external_tool_call_id="tc1",
                        function_name="first_tool",
                        arguments=None,
                        round_index=0,
                        sequence_index=0,
                        message_id="msg1",
                        response=ChatMessageToolResponse(content="r1"),
                    ),
                    ChatMessageTool(
                        external_tool_call_id="tc2",
                        function_name="second_tool",
                        arguments=None,
                        round_index=1,
                        sequence_index=0,
                        message_id="msg1",
                        response=ChatMessageToolResponse(content="r2"),
                    ),
                ],
            )
        )
        mock_get_contents.return_value = history

        result, _, _ = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        # Expected: asst(tc1) -> tool(r1) -> asst(tc2) -> tool(r2) -> asst_final -> user
        messages = result.root
        assert len(messages) == 6
        assert isinstance(messages[0], LanguageModelAssistantMessage)
        assert messages[0].tool_calls[0].function.name == "first_tool"
        assert isinstance(messages[1], LanguageModelToolMessage)
        assert messages[1].content == "r1"
        assert isinstance(messages[2], LanguageModelAssistantMessage)
        assert messages[2].tool_calls[0].function.name == "second_tool"
        assert isinstance(messages[3], LanguageModelToolMessage)
        assert messages[3].content == "r2"
        assert messages[4].role.value == "assistant"
        assert messages[5].role.value == "user"

    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_chat_history_with_contents"
    )
    @pytest.mark.ai
    def test_empty_string_response_generates_tool_message(self, mock_get_contents):
        """
        Purpose: A tool call whose response content is "" (empty string) still
            produces a LanguageModelToolMessage with content="".
        Why this matters: OpenAI requires a tool response message for every tool
            call in the request; omitting it for empty responses causes API errors.
        Setup summary: Tool record with content="" → one LanguageModelToolMessage
            with content == "".
        """
        mock_chat_service, mock_content_service, user_msg, history = (
            self._make_history_context(
                assistant_messages=[("msg1", "Tool returned empty string.")],
                tool_call_records=[
                    ChatMessageTool(
                        external_tool_call_id="tc1",
                        function_name="noop",
                        arguments=None,
                        round_index=0,
                        sequence_index=0,
                        message_id="msg1",
                        response=ChatMessageToolResponse(content=""),
                    ),
                ],
            )
        )
        mock_get_contents.return_value = history

        result, _, _ = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        # Empty string content="" is not None, so a LanguageModelToolMessage must be emitted
        messages = result.root
        tool_messages = [m for m in messages if isinstance(m, LanguageModelToolMessage)]
        assert len(tool_messages) == 1
        assert tool_messages[0].content == ""

    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_chat_history_with_contents"
    )
    @pytest.mark.ai
    def test_tool_call_without_response_omitted_to_keep_valid_sequence(
        self, mock_get_contents
    ):
        """
        Purpose: A tool call record with response=None does not produce an
            assistant(tool_calls)+tool message pair in the reconstructed history.
        Why this matters: Including a tool_calls assistant message without a
            corresponding tool response would violate the OpenAI message schema
            and cause a 400 error.
        Setup summary: Tool record with response=None → no LanguageModelAssistantMessage
            with tool_calls and no LanguageModelToolMessage in the result.
        """
        mock_chat_service, mock_content_service, user_msg, history = (
            self._make_history_context(
                assistant_messages=[("msg1", "Tried a tool but got no response.")],
                tool_call_records=[
                    ChatMessageTool(
                        external_tool_call_id="tc_no_resp",
                        function_name="noop",
                        arguments=None,
                        round_index=0,
                        sequence_index=0,
                        message_id="msg1",
                        response=None,
                    ),
                ],
            )
        )
        mock_get_contents.return_value = history

        result, _, _ = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        messages = result.root
        tool_assistant_msgs = [
            m
            for m in messages
            if isinstance(m, LanguageModelAssistantMessage) and m.tool_calls
        ]
        assert tool_assistant_msgs == []
        tool_messages = [m for m in messages if isinstance(m, LanguageModelToolMessage)]
        assert tool_messages == []

    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_chat_history_with_contents"
    )
    @pytest.mark.ai
    def test_empty_external_id_tool_call_ids_match(self, mock_get_contents):
        """
        Purpose: When external_tool_call_id is "", a valid ID is generated and
            the assistant message's tool_call.id matches the tool response's
            tool_call_id.
        Why this matters: Mismatched IDs cause OpenAI to reject the request with
            an "unmatched tool call id" error.
        Setup summary: Tool record with external_tool_call_id="" → assistant
            tool_calls[0].id != "" and equals tool message's tool_call_id.
        """
        mock_chat_service, mock_content_service, user_msg, history = (
            self._make_history_context(
                assistant_messages=[("msg1", "Used a tool with empty id.")],
                tool_call_records=[
                    ChatMessageTool(
                        external_tool_call_id="",
                        function_name="tool_x",
                        arguments=None,
                        round_index=0,
                        sequence_index=0,
                        message_id="msg1",
                        response=ChatMessageToolResponse(content="ok"),
                    ),
                ],
            )
        )
        mock_get_contents.return_value = history

        result, _, _ = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        messages = result.root
        asst_msg = next(
            m
            for m in messages
            if isinstance(m, LanguageModelAssistantMessage) and m.tool_calls
        )
        tool_msg = next(m for m in messages if isinstance(m, LanguageModelToolMessage))
        # The randomize_id validator replaces "" with a UUID in LanguageModelFunction.
        # Both the assistant message's tool_call id and the tool response's
        # tool_call_id must reference that same (possibly randomized) id.
        assigned_id = asst_msg.tool_calls[0].id
        assert assigned_id != ""
        assert tool_msg.tool_call_id == assigned_id

    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_chat_history_with_contents"
    )
    @pytest.mark.ai
    def test_sdk_failure_falls_back_to_history_without_tool_calls(
        self, mock_get_contents
    ):
        """
        Purpose: A RuntimeError from get_message_tools causes the function to fall
            back to plain chat history with no tool messages, rather than propagating
            the exception.
        Why this matters: A DB failure during history loading must not crash the
            agentic loop; the assistant can still answer from conversation text.
        Setup summary: get_message_tools raises RuntimeError → result has no
            LanguageModelToolMessage, length 2, with assistant then user.
        """
        from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
            ChatHistoryWithContent,
            ChatMessageWithContents,
        )

        mock_chat_service = MagicMock()
        mock_content_service = MagicMock()
        mock_content_service.search_contents.return_value = []
        mock_chat_service.get_full_history.return_value = [
            ChatMessage(
                id="msg1",
                chat_id="chat1",
                role=ChatMessageRole.ASSISTANT,
                text="answer",
                created_at=datetime(2026, 1, 1, 0, 0, 0),
            )
        ]
        mock_chat_service.get_message_tools.side_effect = RuntimeError("DB down")

        user_msg = MagicMock()
        user_msg.id = "u1"
        user_msg.text = "hi"
        user_msg.original_text = "hi"
        user_msg.created_at = "2026-01-01T00:01:00"

        mock_get_contents.return_value = ChatHistoryWithContent(
            root=[
                ChatMessageWithContents(
                    id="msg1",
                    chat_id="chat1",
                    role=ChatMessageRole.ASSISTANT,
                    text="answer",
                    originalText="answer",
                    created_at=datetime(2026, 1, 1, 0, 0, 0),
                ),
                ChatMessageWithContents(
                    chat_id="chat1",
                    role=ChatMessageRole.USER,
                    text="hi",
                    originalText="hi",
                    created_at=datetime(2026, 1, 1, 0, 1, 0),
                ),
            ]
        )

        result, _, _ = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        # No tool messages should be present — falls back gracefully
        messages = result.root
        assert not any(isinstance(m, LanguageModelToolMessage) for m in messages)
        assert len(messages) == 2
        assert messages[0].role.value == "assistant"
        assert messages[1].role.value == "user"

    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_chat_history_with_contents"
    )
    @pytest.mark.ai
    def test_user_only_history(self, mock_get_contents):
        """
        Purpose: A chat with no assistant messages and no tool calls produces a
            single-message history containing only the user message.
        Why this matters: This is the first-message edge case; any spurious tool
            or assistant messages would make the resulting history malformed.
        Setup summary: Empty DB history, single user content message → result
            has one message with role "user".
        """
        mock_chat_service = MagicMock()
        mock_content_service = MagicMock()
        mock_content_service.search_contents.return_value = []

        user_msg = MagicMock()
        user_msg.id = "um1"
        user_msg.text = "Hello"
        user_msg.original_text = "Hello"
        user_msg.created_at = "2026-01-01T00:00:00"

        mock_chat_service.get_full_history.return_value = []
        mock_chat_service.get_message_tools.return_value = []

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

        result, _, _ = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        assert isinstance(result, LanguageModelMessages)
        assert len(result.root) == 1
        assert result.root[0].role.value == "user"


class TestCompactMessageTools:
    def _make_sources(self, source_numbers: list[int]) -> str:
        return json.dumps(
            [
                {"source_number": n, "content": f"content for {n}"}
                for n in source_numbers
            ]
        )

    def _make_record(self, response_content: str | None = None) -> ChatMessageTool:
        return ChatMessageTool(
            external_tool_call_id="call_1",
            function_name="search",
            arguments={"q": "test"},
            round_index=0,
            sequence_index=0,
            response=ChatMessageToolResponse(content=response_content)
            if response_content is not None
            else None,
        )

    @pytest.mark.ai
    def test_no_assistant_text_returns_records_unchanged(self):
        """
        Purpose: When assistant_text is None, compaction is skipped and records
            are returned as-is.
        Why this matters: Compaction requires knowledge of which sources were cited;
            without the assistant text there is no safe basis for removal.
        Setup summary: Three sources, assistant_text=None → response content unchanged.
        """
        content = self._make_sources([0, 1, 2])
        records = [self._make_record(content)]
        result = HistoryManager.compact_message_tools(
            records=records, assistant_text=None
        )
        assert result[0].response.content == content

    @pytest.mark.ai
    def test_empty_assistant_text_returns_records_unchanged(self):
        """
        Purpose: An empty assistant text string does not trigger compaction.
        Why this matters: An empty response contains no citations, so removing
            sources would silently discard potentially useful context.
        Setup summary: Three sources, assistant_text="" → response content unchanged.
        """
        content = self._make_sources([0, 1, 2])
        records = [self._make_record(content)]
        result = HistoryManager.compact_message_tools(
            records=records, assistant_text=""
        )
        assert result[0].response.content == content

    @pytest.mark.ai
    def test_no_citations_returns_records_unchanged(self):
        """
        Purpose: An assistant text with no [sourceN] patterns leaves all records
            untouched.
        Why this matters: If the assistant chose not to cite any source the tool
            results should be preserved for potential future turns.
        Setup summary: Three sources, assistant text with no [source…] tokens
            → response content unchanged.
        """
        content = self._make_sources([0, 1, 2])
        records = [self._make_record(content)]
        result = HistoryManager.compact_message_tools(
            records=records, assistant_text="No sources used here."
        )
        assert result[0].response.content == content

    @pytest.mark.ai
    def test_strips_uncited_sources(self):
        """
        Purpose: Only sources whose source_number appears as [sourceN] in the
            assistant text are kept; the rest are removed.
        Why this matters: Compaction reduces token usage in subsequent turns by
            dropping sources that were not referenced in the final answer.
        Setup summary: Five sources [0-4], assistant cites 0 and 3 → result
            contains exactly those two entries.
        """
        content = self._make_sources([0, 1, 2, 3, 4])
        records = [self._make_record(content)]
        result = HistoryManager.compact_message_tools(
            records=records,
            assistant_text="The answer is sunny [source0] and warm [source3].",
        )
        parsed = json.loads(result[0].response.content)
        assert len(parsed) == 2
        assert {item["source_number"] for item in parsed} == {0, 3}

    @pytest.mark.ai
    def test_keeps_all_when_all_cited(self):
        """
        Purpose: When all sources are cited nothing is stripped.
        Why this matters: Compaction must never remove sources that are actually
            used by the assistant response.
        Setup summary: Two sources both cited → both entries remain.
        """
        content = self._make_sources([5, 6])
        records = [self._make_record(content)]
        result = HistoryManager.compact_message_tools(
            records=records,
            assistant_text="Info from [source5] and [source6].",
        )
        parsed = json.loads(result[0].response.content)
        assert len(parsed) == 2

    @pytest.mark.ai
    def test_non_json_content_left_unchanged(self):
        """
        Purpose: A response whose content is not valid JSON is left unchanged
            rather than crashing or being cleared.
        Why this matters: Legacy or non-search tools may return plain text;
            compaction must degrade gracefully for them.
        Setup summary: response content = "plain text result" → content unchanged.
        """
        records = [self._make_record("plain text result")]
        result = HistoryManager.compact_message_tools(
            records=records, assistant_text="Used [source0] here."
        )
        assert result[0].response.content == "plain text result"

    @pytest.mark.ai
    def test_no_response_record_is_safe(self):
        """
        Purpose: A record with response=None is passed through without raising.
        Why this matters: Tools that crash before returning leave response=None;
            compaction must not blow up on those records.
        Setup summary: Record with response=None → result[0].response is None.
        """
        records = [self._make_record(None)]
        records[0].response = None
        result = HistoryManager.compact_message_tools(
            records=records, assistant_text="Used [source0] here."
        )
        assert result[0].response is None

    @pytest.mark.ai
    def test_multiple_records_compacted_independently(self):
        """
        Purpose: Each tool call record is compacted against the shared assistant
            text independently; cited source numbers from different records are
            correctly attributed to their own record.
        Why this matters: Sources from different tool calls must not bleed into
            each other during compaction — only entries matching cited numbers
            within that record should survive.
        Setup summary: Two records with sources [0,1,2] and [3,4,5]; assistant
            cites 1 and 4 → each record retains only its cited entry.
        """
        r1 = self._make_record(self._make_sources([0, 1, 2]))
        r2 = ChatMessageTool(
            external_tool_call_id="call_2",
            function_name="web_search",
            arguments={"q": "weather"},
            round_index=1,
            sequence_index=0,
            response=ChatMessageToolResponse(content=self._make_sources([3, 4, 5])),
        )
        result = HistoryManager.compact_message_tools(
            records=[r1, r2],
            assistant_text="From [source1] and [source4] we know...",
        )
        parsed_r1 = json.loads(result[0].response.content)
        parsed_r2 = json.loads(result[1].response.content)
        assert len(parsed_r1) == 1
        assert parsed_r1[0]["source_number"] == 1
        assert len(parsed_r2) == 1
        assert parsed_r2[0]["source_number"] == 4

    @pytest.mark.ai
    def test_case_insensitive_citation_matching(self):
        """
        Purpose: Citation matching is case-insensitive so [Source0] and [source0]
            both count as a reference to source 0.
        Why this matters: The LLM may capitalise "Source"; failing to match it
            case-insensitively would cause valid citations to be stripped.
        Setup summary: Two sources, assistant uses "[Source0]" (capital S) → only
            source 0 retained.
        """
        content = self._make_sources([0, 1])
        records = [self._make_record(content)]
        result = HistoryManager.compact_message_tools(
            records=records,
            assistant_text="Per [Source0] this is correct.",
        )
        parsed = json.loads(result[0].response.content)
        assert len(parsed) == 1
        assert parsed[0]["source_number"] == 0

    def test_preserves_readable_unicode_when_stripping_uncited_sources(self):
        content = json.dumps(
            [
                {
                    "source_number": 0,
                    "content_id": "cont_0",
                    "content": 'ページ名 "quoted" / مرحبا 😀',
                },
                {
                    "source_number": 1,
                    "content_id": "cont_1",
                    "content": "other",
                },
            ],
            ensure_ascii=False,
        )
        records = [self._make_record(content)]

        result = HistoryManager.compact_message_tools(
            records=records,
            assistant_text="Only [source0] is cited.",
        )

        compacted_content = result[0].response.content
        assert "ページ名" in compacted_content
        assert "مرحبا" in compacted_content
        assert "😀" in compacted_content
        assert "\\u30da" not in compacted_content
        assert "\\ud83d" not in compacted_content
        assert json.loads(compacted_content) == [
            {
                "source_number": 0,
                "content_id": "cont_0",
                "content": 'ページ名 "quoted" / مرحبا 😀',
            }
        ]
