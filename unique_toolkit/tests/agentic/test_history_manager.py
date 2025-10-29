import logging
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from tests.test_obj_factory import get_event_obj
from unique_toolkit.agentic.history_manager.history_manager import (
    HistoryManager,
    HistoryManagerConfig,
    UploadedContentConfig,
)
from unique_toolkit.agentic.reference_manager.reference_manager import ReferenceManager
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessages,
    LanguageModelToolMessage,
)


@pytest.fixture
def mock_logger():
    return Mock(spec=logging.Logger)


@pytest.fixture
def chat_event():
    return get_event_obj(
        user_id="test_user",
        company_id="test_company",
        chat_id="test_chat",
        assistant_id="test_assistant",
        user_message_id="test_user_message",
    )


@pytest.fixture
def history_manager_config():
    return HistoryManagerConfig(
        percent_of_max_tokens_for_history=0.2,
        language_model=LanguageModelInfo.from_name(DEFAULT_GPT_4o),
        uploaded_content_config=UploadedContentConfig(),
    )


@pytest.fixture
def mock_reference_manager():
    return Mock(spec=ReferenceManager)


@pytest.fixture
def history_manager(mock_logger, chat_event, history_manager_config, mock_reference_manager):
    return HistoryManager(
        logger=mock_logger,
        event=chat_event,
        config=history_manager_config,
        language_model=LanguageModelInfo.from_name(DEFAULT_GPT_4o),
        reference_manager=mock_reference_manager,
    )


class TestHistoryManagerConfig:
    @pytest.mark.unit
    def test_default_config_values(self):
        config = HistoryManagerConfig()
        
        assert config.percent_of_max_tokens_for_history == 0.2
        assert config.language_model is not None
        assert isinstance(config.uploaded_content_config, UploadedContentConfig)

    @pytest.mark.unit
    def test_max_history_tokens_property(self):
        config = HistoryManagerConfig(
            percent_of_max_tokens_for_history=0.3,
            language_model=LanguageModelInfo.from_name(DEFAULT_GPT_4o),
        )
        
        expected_max_tokens = int(
            config.language_model.token_limits.token_limit_input * 0.3
        )
        assert config.max_history_tokens == expected_max_tokens

    @pytest.mark.unit
    def test_uploaded_content_config_defaults(self):
        config = UploadedContentConfig()
        
        assert config.percent_for_uploaded_content == 0.6
        assert "uploaded content is too large" in config.user_context_window_limit_warning.lower()


class TestHistoryManager:
    @pytest.mark.unit
    def test_initialization(self, history_manager, mock_logger, history_manager_config):
        assert history_manager._config == history_manager_config
        assert history_manager._logger == mock_logger
        assert history_manager._tool_call_result_history == []
        assert history_manager._tool_calls == []
        assert history_manager._internal_tool_calls == []
        assert history_manager._mcp_tool_calls == []
        assert history_manager._sub_agent_calls == []
        assert history_manager._loop_history == []
        assert history_manager._source_enumerator == 0

    @pytest.mark.unit
    def test_add_tool_call(self, history_manager):
        tool_call = LanguageModelFunction(
            id="tool_1",
            name="test_tool",
            arguments='{"arg": "value"}',
        )
        
        history_manager.add_tool_call(tool_call)
        
        assert len(history_manager.get_tool_calls()) == 1
        assert history_manager.get_tool_calls()[0] == tool_call

    @pytest.mark.unit
    def test_add_internal_tool_call(self, history_manager):
        tool_call = LanguageModelFunction(
            id="internal_1",
            name="internal_tool",
            arguments='{"arg": "value"}',
        )
        
        history_manager.add_internal_tool_call(tool_call)
        
        assert len(history_manager.get_internal_tool_calls()) == 1
        assert history_manager.get_internal_tool_calls()[0] == tool_call

    @pytest.mark.unit
    def test_add_mcp_tool_call(self, history_manager):
        tool_call = LanguageModelFunction(
            id="mcp_1",
            name="mcp_tool",
            arguments='{"arg": "value"}',
        )
        
        history_manager.add_mcp_tool_call(tool_call)
        
        assert len(history_manager.get_mcp_tool_calls()) == 1
        assert history_manager.get_mcp_tool_calls()[0] == tool_call

    @pytest.mark.unit
    def test_add_sub_agent_call(self, history_manager):
        tool_call = LanguageModelFunction(
            id="agent_1",
            name="sub_agent",
            arguments='{"arg": "value"}',
        )
        
        history_manager.add_sub_agent_call(tool_call)
        
        assert len(history_manager.get_sub_agent_calls()) == 1
        assert history_manager.get_sub_agent_calls()[0] == tool_call

    @pytest.mark.unit
    def test_has_no_loop_messages_initially_true(self, history_manager):
        assert history_manager.has_no_loop_messages() is True

    @pytest.mark.unit
    def test_has_no_loop_messages_false_after_adding(self, history_manager):
        message = LanguageModelAssistantMessage(content="test")
        history_manager.add_assistant_message(message)
        
        assert history_manager.has_no_loop_messages() is False

    @pytest.mark.unit
    def test_add_assistant_message(self, history_manager):
        message = LanguageModelAssistantMessage(content="Assistant response")
        
        history_manager.add_assistant_message(message)
        
        assert len(history_manager._loop_history) == 1
        assert history_manager._loop_history[0] == message

    @pytest.mark.unit
    def test_add_tool_call_results_successful(self, history_manager):
        tool_response = ToolCallResponse(
            id="tool_1",
            name="test_tool",
            content="Tool result content",
        )
        
        history_manager.add_tool_call_results([tool_response])
        
        assert len(history_manager._loop_history) == 1
        message = history_manager._loop_history[0]
        assert isinstance(message, LanguageModelToolMessage)
        assert message.content == "Tool result content"
        assert message.tool_call_id == "tool_1"
        assert message.name == "test_tool"

    @pytest.mark.unit
    def test_add_tool_call_results_failed(self, history_manager):
        tool_response = ToolCallResponse(
            id="tool_2",
            name="failed_tool",
            content="",
            error_message="Tool execution failed",
        )
        
        history_manager.add_tool_call_results([tool_response])
        
        assert len(history_manager._loop_history) == 1
        message = history_manager._loop_history[0]
        assert isinstance(message, LanguageModelToolMessage)
        assert "" == message.content
        assert "Tool execution failed" == message.content
        assert message.tool_call_id == "tool_2"
        assert message.name == "failed_tool"

    @pytest.mark.unit
    def test_add_tool_call_results_with_content_chunks(self, history_manager):
        content_chunks = [
            ContentChunk(
                id="chunk_1",
                chunk_id="1",
                key="test_key",
                order=1,
                text="Chunk content 1",
            ),
            ContentChunk(
                id="chunk_2",
                chunk_id="2",
                key="test_key",
                order=2,
                text="Chunk content 2",
            ),
        ]
        
        tool_response = ToolCallResponse(
            id="tool_3",
            name="search_tool",
            content="",
            content_chunks=content_chunks,
            error_message="",
        )
        
        history_manager.add_tool_call_results([tool_response])
        
        assert len(history_manager._loop_history) == 1
        message = history_manager._loop_history[0]
        assert isinstance(message, LanguageModelToolMessage)
        assert message.tool_call_id == "tool_3"
        assert history_manager._source_enumerator == 2  # Two chunks added

    @pytest.mark.unit
    def test_add_multiple_tool_call_results(self, history_manager):
        responses = [
            ToolCallResponse(
                id="tool_1",
                name="tool_1",
                content="Result 1",
                error_message="",
            ),
            ToolCallResponse(
                id="tool_2",
                name="tool_2",
                content="Result 2",
                error_message="",
            ),
            ToolCallResponse(
                id="tool_3",
                name="tool_3",
                content="",
                error_message="Error 3",
            ),
        ]
        
        history_manager.add_tool_call_results(responses)
        
        assert len(history_manager._loop_history) == 3
        assert history_manager._loop_history[0].content == "Result 1"
        assert history_manager._loop_history[1].content == "Result 2"
        assert "Error 3" in history_manager._loop_history[2].content

    @pytest.mark.unit
    @patch("unique_toolkit.agentic.history_manager.history_manager.LoopTokenReducer")
    def test_append_tool_calls_to_history(self, mock_reducer, history_manager):
        tool_calls = [
            LanguageModelFunction(
                id="tool_1",
                name="test_tool_1",
                arguments='{"arg": "value1"}',
            ),
            LanguageModelFunction(
                id="tool_2",
                name="test_tool_2",
                arguments='{"arg": "value2"}',
            ),
        ]
        
        history_manager._append_tool_calls_to_history(tool_calls)
        
        assert len(history_manager._loop_history) == 1
        message = history_manager._loop_history[0]
        assert isinstance(message, LanguageModelAssistantMessage)
        assert message.tool_calls == tool_calls

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_history_for_model_call(self, history_manager):
        # Mock the token reducer's method
        mock_messages = LanguageModelMessages([
            LanguageModelAssistantMessage(content="test")
        ])
        history_manager._token_reducer.get_history_for_model_call = AsyncMock(
            return_value=mock_messages
        )
        
        async def mock_remove_from_text(text: str) -> str:
            return text.replace("remove", "")
        
        result = await history_manager.get_history_for_model_call(
            original_user_message="Original message",
            rendered_user_message_string="Rendered message",
            rendered_system_message_string="System message",
            remove_from_text=mock_remove_from_text,
        )
        
        assert result == mock_messages
        history_manager._token_reducer.get_history_for_model_call.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_visible_chat_history_without_assistant_message(
        self, history_manager
    ):
        # Mock the token reducer's method
        mock_history = [
            LanguageModelAssistantMessage(content="Previous message")
        ]
        history_manager._token_reducer.get_history_from_db = AsyncMock(
            return_value=mock_history
        )
        
        result = await history_manager.get_user_visible_chat_history()
        
        assert len(result.root) == 1
        assert result.root[0].content == "Previous message"
        history_manager._token_reducer.get_history_from_db.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_visible_chat_history_with_assistant_message(
        self, history_manager
    ):
        # Mock the token reducer's method
        mock_history = [
            LanguageModelAssistantMessage(content="Previous message")
        ]
        history_manager._token_reducer.get_history_from_db = AsyncMock(
            return_value=mock_history
        )
        
        result = await history_manager.get_user_visible_chat_history(
            assistant_message_text="New assistant message"
        )
        
        assert len(result.root) == 2
        assert result.root[0].content == "Previous message"
        assert result.root[1].content == "New assistant message"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_visible_chat_history_with_remove_from_text(
        self, history_manager
    ):
        # Mock the token reducer's method
        mock_history = [
            LanguageModelAssistantMessage(content="Message with removable content")
        ]
        history_manager._token_reducer.get_history_from_db = AsyncMock(
            return_value=mock_history
        )
        
        async def mock_remove_from_text(text: str) -> str:
            return text.replace("removable", "cleaned")
        
        result = await history_manager.get_user_visible_chat_history(
            remove_from_text=mock_remove_from_text
        )
        
        history_manager._token_reducer.get_history_from_db.assert_called_once_with(
            mock_remove_from_text
        )

    @pytest.mark.unit
    def test_source_enumerator_increments_correctly(self, history_manager):
        # Test that source enumerator increments for each chunk
        content_chunks_1 = [
            ContentChunk(
                id="chunk_1",
                chunk_id="1",
                key="key",
                order=1,
                text="Text 1",
            ),
        ]
        
        content_chunks_2 = [
            ContentChunk(
                id="chunk_2",
                chunk_id="2",
                key="key",
                order=1,
                text="Text 2",
            ),
            ContentChunk(
                id="chunk_3",
                chunk_id="3",
                key="key",
                order=2,
                text="Text 3",
            ),
        ]
        
        tool_response_1 = ToolCallResponse(
            id="tool_1",
            name="tool_1",
            content="",
            content_chunks=content_chunks_1,
            error_message="",
        )
        
        tool_response_2 = ToolCallResponse(
            id="tool_2",
            name="tool_2",
            content="",
            content_chunks=content_chunks_2,
            error_message="",
        )
        
        history_manager.add_tool_call_results([tool_response_1])
        assert history_manager._source_enumerator == 1
        
        history_manager.add_tool_call_results([tool_response_2])
        assert history_manager._source_enumerator == 3

    @pytest.mark.unit
    def test_logger_debug_called_when_appending_tool_result(
        self, history_manager, mock_logger
    ):
        tool_response = ToolCallResponse(
            id="tool_1",
            name="debug_tool",
            content="Content",
            error_message="",
        )
        
        history_manager.add_tool_call_results([tool_response])
        
        # Verify logger.debug was called
        mock_logger.debug.assert_called()
        debug_call_args = mock_logger.debug.call_args[0][0]
        assert "debug_tool" in debug_call_args

    @pytest.mark.unit
    def test_multiple_tool_call_types_tracked_separately(self, history_manager):
        regular_tool = LanguageModelFunction(
            id="regular", name="regular_tool", arguments="{}"
        )
        internal_tool = LanguageModelFunction(
            id="internal", name="internal_tool", arguments="{}"
        )
        mcp_tool = LanguageModelFunction(
            id="mcp", name="mcp_tool", arguments="{}"
        )
        agent_tool = LanguageModelFunction(
            id="agent", name="agent_tool", arguments="{}"
        )
        
        history_manager.add_tool_call(regular_tool)
        history_manager.add_internal_tool_call(internal_tool)
        history_manager.add_mcp_tool_call(mcp_tool)
        history_manager.add_sub_agent_call(agent_tool)
        
        assert len(history_manager.get_tool_calls()) == 1
        assert len(history_manager.get_internal_tool_calls()) == 1
        assert len(history_manager.get_mcp_tool_calls()) == 1
        assert len(history_manager.get_sub_agent_calls()) == 1
        
        assert history_manager.get_tool_calls()[0].name == "regular_tool"
        assert history_manager.get_internal_tool_calls()[0].name == "internal_tool"
        assert history_manager.get_mcp_tool_calls()[0].name == "mcp_tool"
        assert history_manager.get_sub_agent_calls()[0].name == "agent_tool"


class TestHistoryManagerEdgeCases:
    @pytest.mark.unit
    def test_empty_content_chunks_list(self, history_manager):
        tool_response = ToolCallResponse(
            id="tool_1",
            name="test_tool",
            content="",
            content_chunks=[],
            error_message="",
        )
        
        history_manager.add_tool_call_results([tool_response])
        
        assert len(history_manager._loop_history) == 1
        message = history_manager._loop_history[0]
        assert isinstance(message, LanguageModelToolMessage)

    @pytest.mark.unit
    def test_none_content_chunks(self, history_manager):
        tool_response = ToolCallResponse(
            id="tool_1",
            name="test_tool",
            content="",
            content_chunks=None,
            error_message="",
        )
        
        history_manager.add_tool_call_results([tool_response])
        
        assert len(history_manager._loop_history) == 1

    @pytest.mark.unit
    def test_empty_tool_call_results_list(self, history_manager):
        history_manager.add_tool_call_results([])
        
        assert len(history_manager._loop_history) == 0

    @pytest.mark.unit
    def test_config_without_uploaded_content(self, mock_logger, chat_event, mock_reference_manager):
        config = HistoryManagerConfig(
            uploaded_content_config=None
        )
        
        manager = HistoryManager(
            logger=mock_logger,
            event=chat_event,
            config=config,
            language_model=LanguageModelInfo.from_name(DEFAULT_GPT_4o),
            reference_manager=mock_reference_manager,
        )
        
        assert manager._config.uploaded_content_config is None
