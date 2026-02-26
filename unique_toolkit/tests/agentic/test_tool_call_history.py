import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from unique_toolkit.agentic.history_manager.history_construction_with_contents import (
    _parse_tool_calls_from_gpt_request,
    get_full_history_with_contents_and_tool_calls,
)
from unique_toolkit.chat.functions import (
    _construct_message_create_params,
    _filter_valid_messages_including_tools,
    create_tool_call_message,
    create_tool_message,
    filter_valid_messages,
)
from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunctionCall,
    LanguageModelMessages,
    LanguageModelToolMessage,
)


class TestChatMessageRole:
    def test_tool_call_role_exists(self):
        assert ChatMessageRole.TOOL_CALL == "tool_call"
        assert ChatMessageRole.TOOL_CALL.value == "tool_call"

    def test_tool_role_exists(self):
        assert ChatMessageRole.TOOL == "tool"

    def test_tool_call_role_uppercased(self):
        assert ChatMessageRole.TOOL_CALL.value.upper() == "TOOL_CALL"


class TestConstructMessageCreateParams:
    def test_tool_call_role_param(self):
        params = _construct_message_create_params(
            user_id="u1",
            company_id="c1",
            chat_id="chat1",
            assistant_id="a1",
            role=ChatMessageRole.TOOL_CALL,
            gpt_request={"tool_calls": [{"id": "tc1", "type": "function"}]},
        )
        assert params["role"] == "TOOL_CALL"
        assert params["gptRequest"] == {
            "tool_calls": [{"id": "tc1", "type": "function"}]
        }

    def test_tool_role_param(self):
        params = _construct_message_create_params(
            user_id="u1",
            company_id="c1",
            chat_id="chat1",
            assistant_id="a1",
            role=ChatMessageRole.TOOL,
            content="tool response",
            gpt_request={"tool_call_id": "tc1", "name": "search"},
        )
        assert params["role"] == "TOOL"
        assert params["text"] == "tool response"
        assert params["gptRequest"] == {"tool_call_id": "tc1", "name": "search"}

    def test_assistant_role_param_unchanged(self):
        params = _construct_message_create_params(
            user_id="u1",
            company_id="c1",
            chat_id="chat1",
            assistant_id="a1",
            role=ChatMessageRole.ASSISTANT,
            content="hello",
        )
        assert params["role"] == "ASSISTANT"
        assert "gptRequest" not in params

    def test_gpt_request_omitted_when_none(self):
        params = _construct_message_create_params(
            user_id="u1",
            company_id="c1",
            chat_id="chat1",
            assistant_id="a1",
            role=ChatMessageRole.ASSISTANT,
        )
        assert "gptRequest" not in params


class TestCreateToolCallMessage:
    @patch("unique_toolkit.chat.functions.unique_sdk")
    def test_creates_tool_call_message(self, mock_sdk):
        mock_sdk.Message.create.return_value = {
            "id": "msg1",
            "chatId": "chat1",
            "role": "TOOL_CALL",
            "text": None,
            "gptRequest": [{"tool_calls": []}],
        }

        result = create_tool_call_message(
            user_id="u1",
            company_id="c1",
            chat_id="chat1",
            assistant_id="a1",
            tool_calls_data=[
                {
                    "id": "tc1",
                    "type": "function",
                    "function": {"name": "search", "arguments": {"q": "test"}},
                }
            ],
        )

        assert isinstance(result, ChatMessage)
        mock_sdk.Message.create.assert_called_once()
        call_kwargs = mock_sdk.Message.create.call_args
        assert call_kwargs.kwargs.get("role") == "TOOL_CALL"


class TestCreateToolMessage:
    @patch("unique_toolkit.chat.functions.unique_sdk")
    def test_creates_tool_message(self, mock_sdk):
        mock_sdk.Message.create.return_value = {
            "id": "msg2",
            "chatId": "chat1",
            "role": "TOOL",
            "text": "search results...",
            "toolCallId": "tc1",
            "gptRequest": [{"tool_call_id": "tc1", "name": "search"}],
        }

        result = create_tool_message(
            user_id="u1",
            company_id="c1",
            chat_id="chat1",
            assistant_id="a1",
            tool_call_id="tc1",
            tool_name="search",
            content="search results...",
        )

        assert isinstance(result, ChatMessage)
        mock_sdk.Message.create.assert_called_once()


class TestFilterValidMessages:
    def _make_messages(self, roles_and_texts):
        data = []
        for role, text in roles_and_texts:
            data.append({"role": role, "text": text})
        return {
            "data": data
            + [
                {"role": "USER", "text": "last1"},
                {"role": "ASSISTANT", "text": "last2"},
            ]
        }

    def test_filters_tool_call_and_tool(self):
        msgs = self._make_messages(
            [
                ("USER", "hello"),
                ("ASSISTANT", "world"),
                ("TOOL_CALL", None),
                ("TOOL", "tool response"),
            ]
        )
        result = filter_valid_messages(msgs)
        roles = [m["role"] for m in result]
        assert "TOOL_CALL" not in [r.lower() for r in roles]
        assert "TOOL" not in [r.lower() for r in roles]
        assert len(result) == 2

    def test_keeps_user_and_assistant(self):
        msgs = self._make_messages(
            [
                ("USER", "q1"),
                ("ASSISTANT", "a1"),
            ]
        )
        result = filter_valid_messages(msgs)
        assert len(result) == 2


class TestFilterValidMessagesIncludingTools:
    def _make_messages(self, roles_and_texts):
        data = []
        for role, text in roles_and_texts:
            data.append({"role": role, "text": text})
        return {
            "data": data
            + [
                {"role": "USER", "text": "last1"},
                {"role": "ASSISTANT", "text": "last2"},
            ]
        }

    def test_keeps_tool_call_and_tool(self):
        msgs = self._make_messages(
            [
                ("USER", "hello"),
                ("TOOL_CALL", None),
                ("TOOL", "tool response"),
                ("ASSISTANT", "final answer"),
            ]
        )
        result = _filter_valid_messages_including_tools(msgs)
        roles = [m["role"] for m in result]
        assert "TOOL_CALL" in roles
        assert "TOOL" in roles
        assert len(result) == 4

    def test_filters_system(self):
        msgs = self._make_messages(
            [
                ("SYSTEM", "system msg"),
                ("USER", "hello"),
            ]
        )
        result = _filter_valid_messages_including_tools(msgs)
        assert len(result) == 1
        assert result[0]["role"] == "USER"

    def test_tool_call_with_null_text_kept(self):
        msgs = self._make_messages(
            [
                ("TOOL_CALL", None),
            ]
        )
        result = _filter_valid_messages_including_tools(msgs)
        assert len(result) == 1


class TestParseToolCallsFromGptRequest:
    def test_parses_tool_calls(self):
        data = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "web_search",
                    "arguments": {"query": "test"},
                },
            }
        ]
        result = _parse_tool_calls_from_gpt_request(data)
        assert len(result) == 1
        assert isinstance(result[0], LanguageModelFunctionCall)
        assert result[0].function.name == "web_search"
        assert result[0].function.arguments == {"query": "test"}

    def test_parses_string_arguments(self):
        data = [
            {
                "id": "call_2",
                "type": "function",
                "function": {
                    "name": "search",
                    "arguments": json.dumps({"q": "hello"}),
                },
            }
        ]
        result = _parse_tool_calls_from_gpt_request(data)
        assert result[0].function.arguments == {"q": "hello"}

    def test_empty_input(self):
        assert _parse_tool_calls_from_gpt_request([]) == []


class TestGetFullHistoryWithContentsAndToolCalls:
    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_full_history_including_tool_messages"
    )
    def test_builds_history_with_tool_messages(self, mock_get_history):
        mock_chat_service = MagicMock()
        mock_chat_service._user_id = "u1"
        mock_chat_service._company_id = "c1"

        mock_content_service = MagicMock()
        mock_content_service.search_contents.return_value = []

        user_msg = MagicMock()
        user_msg.id = "msg5"
        user_msg.text = "And what is 3+3?"
        user_msg.original_text = "And what is 3+3?"
        user_msg.created_at = "2026-01-01T00:00:04"

        mock_get_history.return_value = [
            ChatMessage(
                id="msg1",
                chat_id="chat1",
                role=ChatMessageRole.USER,
                text="What is 2+2?",
                created_at=datetime(2026, 1, 1, 0, 0, 0),
            ),
            ChatMessage(
                id="msg2",
                chat_id="chat1",
                role=ChatMessageRole.TOOL_CALL,
                text=None,
                gpt_request={
                    "tool_calls": [
                        {
                            "id": "tc1",
                            "type": "function",
                            "function": {
                                "name": "calculator",
                                "arguments": {"expr": "2+2"},
                            },
                        }
                    ]
                },
                created_at=datetime(2026, 1, 1, 0, 0, 1),
            ),
            ChatMessage(
                id="msg3",
                chat_id="chat1",
                role=ChatMessageRole.TOOL,
                text="4",
                tool_call_id="tc1",
                gpt_request={"tool_call_id": "tc1", "name": "calculator"},
                created_at=datetime(2026, 1, 1, 0, 0, 2),
            ),
            ChatMessage(
                id="msg4",
                chat_id="chat1",
                role=ChatMessageRole.ASSISTANT,
                text="The answer is 4.",
                created_at=datetime(2026, 1, 1, 0, 0, 3),
            ),
        ]

        result = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        assert isinstance(result, LanguageModelMessages)
        assert len(result.root) == 5

        # msg1: user "What is 2+2?"
        assert result.root[0].role.value == "user"
        # msg2: TOOL_CALL -> mapped to assistant with tool_calls
        assert isinstance(result.root[1], LanguageModelAssistantMessage)
        assert result.root[1].tool_calls is not None
        assert len(result.root[1].tool_calls) == 1
        assert result.root[1].tool_calls[0].function.name == "calculator"
        # msg3: TOOL -> mapped to tool message
        assert isinstance(result.root[2], LanguageModelToolMessage)
        assert result.root[2].content == "4"
        assert result.root[2].tool_call_id == "tc1"
        # msg4: assistant "The answer is 4."
        assert result.root[3].role.value == "assistant"
        # msg5: new user message "And what is 3+3?"
        assert result.root[4].role.value == "user"

    @patch(
        "unique_toolkit.agentic.history_manager.history_construction_with_contents.get_full_history_including_tool_messages"
    )
    def test_user_only_history(self, mock_get_history):
        mock_chat_service = MagicMock()
        mock_chat_service._user_id = "u1"
        mock_chat_service._company_id = "c1"

        mock_content_service = MagicMock()
        mock_content_service.search_contents.return_value = []

        user_msg = MagicMock()
        user_msg.id = "um1"
        user_msg.text = "Hello"
        user_msg.original_text = "Hello"
        user_msg.created_at = "2026-01-01T00:00:00"

        mock_get_history.return_value = []

        result = get_full_history_with_contents_and_tool_calls(
            user_message=user_msg,
            chat_id="chat1",
            chat_service=mock_chat_service,
            content_service=mock_content_service,
        )

        assert isinstance(result, LanguageModelMessages)
        assert len(result.root) == 1
        assert result.root[0].role.value == "user"
