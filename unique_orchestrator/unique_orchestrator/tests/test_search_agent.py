from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from quart import Quart, g
from unique_orchestrator.service import InternalSearchTool
from unique_toolkit.app.schemas import (
    ChatEvent,
    ChatEventAssistantMessage,
    ChatEventPayload,
    ChatEventUserMessage,
    EventName,
)
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelFunctionCall,
    LanguageModelMessages,
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)
from unique_web_search.service import WebSearchTool

from _common.agents.loop_agent.schemas import (
    AgentChunksHandler,
    AgentDebugInfo,
)
from _common.evaluators.schemas import (
    EvaluationMetricName,
    EvaluationMetricResult,
)
from _common.stock_ticker import (
    StockTicker,
    getStockTickersResponse,
)
from agentic_search.config import SearchAgentConfig
from agentic_search.prompts import (
    SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX,
)
from agentic_search.search_agent import SearchAgent
from default_language_model import (
    DEFAULT_GPT_4o,
)


# Base fixtures that other fixtures will use
@pytest.fixture
def app():
    return Quart(__name__)


@pytest.fixture
def base_event_payload():
    return ChatEventPayload(
        name="test_name",
        description="test_description",
        configuration={
            "suggest_follow_up_questions": True,
            "language_model": DEFAULT_GPT_4o.value,
        },
        chat_id="test_chat",
        assistant_id="test_assistant",
        user_message=ChatEventUserMessage(
            id="test_user_message",
            text="test query",
            original_text="test query",
            created_at="2022-01-01T00:00:00Z",
            language="en",
        ),
        assistant_message=ChatEventAssistantMessage(
            id="test_assistant_message",
            created_at="2022-01-01T00:00:00Z",
        ),
    )


@pytest.fixture
def mock_event(base_event_payload):
    return ChatEvent(
        id="test_id",
        event=EventName.EXTERNAL_MODULE_CHOSEN,
        user_id="test_user",
        company_id="test_company",
        payload=base_event_payload,
    )


@pytest.fixture
def mock_content_chunks():
    return [
        ContentChunk(id=f"c_{i}", text=f"Source {i}", order=0)
        for i in range(5)
    ]


@pytest.fixture
def mock_agent_chunks_handler():
    handler = MagicMock(spec=AgentChunksHandler)
    handler.chunks = MagicMock(spec=list[ContentChunk])
    return handler


@pytest.fixture
async def search_agent(app, mock_event, mock_agent_chunks_handler):
    async with app.app_context():
        g.module_name = "Some module"
        agent = SearchAgent(
            event=mock_event,
            config=SearchAgentConfig(**mock_event.payload.configuration),
            agent_debug_info=AgentDebugInfo(),
            agent_chunks_handler=mock_agent_chunks_handler,
        )
        return agent


# Test classes to organize related tests
class TestSearchAgentInitialization:
    @pytest.mark.asyncio
    async def test_encoding_model_initialization(self, app, mock_event):
        async with app.app_context():
            # Test with mock encoder
            g.module_name = "some module"
            with patch(
                "agentic_search.search_agent.get_encoder_name"
            ) as mock_get_encoder:
                mock_get_encoder.return_value = MagicMock(value="mock_encoder")
                agent = SearchAgent(
                    event=mock_event,
                    config=SearchAgentConfig(
                        **mock_event.payload.configuration
                    ),
                )
                assert agent.encoding_model == "mock_encoder"

            # Test with GPT-4o
            mock_event.payload.configuration["language_model"] = DEFAULT_GPT_4o
            agent = SearchAgent(
                event=mock_event,
                config=SearchAgentConfig(**mock_event.payload.configuration),
            )
            assert agent.encoding_model == "o200k_base"


class TestMessageComposition:
    @pytest.fixture
    def mock_messages(self):
        """Fixture providing common message objects."""
        user_message = LanguageModelUserMessage(content="User message")
        system_message = LanguageModelSystemMessage(content="System message")
        combined_message = LanguageModelMessages(
            [user_message, system_message]
        )
        history = LanguageModelMessages([user_message, system_message])
        return {
            "user_message": user_message,
            "system_message": system_message,
            "combined_message": combined_message,
            "history": history,
        }

    @pytest.fixture
    def mock_message_dependencies(self, mocker, search_agent, mock_messages):
        """Fixture setting up all message-related mocks."""
        mocker.patch.object(
            search_agent,
            "_get_user_message_for_plan_execution",
            return_value=mock_messages["user_message"],
        )
        mocker.patch.object(
            search_agent,
            "_get_system_message_for_plan_execution",
            return_value=mock_messages["system_message"],
        )
        mocker.patch.object(
            search_agent,
            "_combine_user_and_system_message_with_history",
            return_value=mock_messages["combined_message"],
        )
        mocker.patch(
            "agentic_search.search_agent.remove_suggested_questions_from_history",
            return_value=mock_messages["history"],
        )

        search_agent.agent_debug_info.add = MagicMock()
        search_agent.logger.info = MagicMock()
        search_agent.logger.warning = MagicMock()
        search_agent.history = []  # Initialize empty history

        return search_agent

    def test_compose_message_plan_execution(
        self, mocker, mock_message_dependencies, mock_messages
    ):
        mocker.patch(
            "agentic_search.search_agent.num_token_for_language_model_messages",
            return_value=1000,
        )
        """Test normal message composition flow."""
        agent = mock_message_dependencies

        messages = agent._compose_message_plan_execution()

        assert messages == mock_messages["combined_message"]
        agent.logger.info.assert_any_call("Token messages: 1000")
        agent.agent_debug_info.add.assert_called_with("token_messages", 1000)
        agent.logger.warning.assert_not_called()

    def test_compose_message_plan_execution_no_chunks(
        self, mocker, mock_message_dependencies, mock_messages
    ):
        """Test message composition with no chunks."""
        agent = mock_message_dependencies
        mocker.patch(
            "agentic_search.search_agent.num_token_for_language_model_messages",
            return_value=3500,
        )

        agent.agent_chunks_handler.chunks = []

        messages = agent._compose_message_plan_execution()

        assert messages == mock_messages["combined_message"]
        agent.logger.info.assert_any_call("Token messages: 3500")
        agent.agent_debug_info.add.assert_called_with("token_messages", 3500)
        agent.logger.warning.assert_not_called()


class TestHandleNoToolCalls:
    @pytest.fixture
    def mock_evaluation_service(self):
        service = MagicMock()
        service.run_evaluation_of_streaming_result = AsyncMock()
        service.inform_user_about_negative_evaluation = MagicMock()
        return service

    @pytest.fixture
    def mock_follow_up_service(self):
        service = AsyncMock()
        service.get_follow_up_question_suggestion = AsyncMock()
        service.append_suggested_question_to_message = AsyncMock()
        return service

    @pytest.fixture
    def mock_stock_ticker_service(self):
        service = MagicMock()
        service.get_stock_tickers = AsyncMock()
        service.append_stock_diagram_to_message = AsyncMock()
        return service

    @pytest.fixture
    def mock_loop_response(self):
        response = AsyncMock()
        response.message.text = "Test response"
        response.tool_calls = None
        return response

    @pytest.fixture
    def configured_search_agent(
        self,
        search_agent,
        mock_evaluation_service,
        mock_follow_up_service,
        mock_stock_ticker_service,
        mock_loop_response,
    ):
        search_agent.evaluation_service = mock_evaluation_service
        search_agent.follow_up_question_service = mock_follow_up_service
        search_agent.stock_ticker_service = mock_stock_ticker_service
        search_agent.loop_response = mock_loop_response
        search_agent._loop_history = []
        search_agent._tool_evaluation_check_list = []
        search_agent.history = []
        search_agent.config.follow_up_questions_config.number_of_follow_up_questions = 3

        search_agent.logger.info = MagicMock()
        search_agent.logger.warning = MagicMock()
        return search_agent

    @pytest.mark.asyncio
    async def test_handle_no_tool_calls_successful_evaluation(
        self, configured_search_agent
    ):
        """Test handling when evaluation passes."""
        agent = configured_search_agent
        agent.chat_service.modify_assistant_message = MagicMock()
        agent.config.follow_up_questions_config.number_of_follow_up_questions = 2
        agent.config.stock_ticker_config.enabled = True

        # Configure mock returns
        agent.evaluation_service.run_evaluation_of_streaming_result.return_value = (
            [],
            True,  # loop_history, evaluation_result_passed
        )
        agent.follow_up_question_service.get_follow_up_question_suggestion.return_value = [
            "Question 1?",
            "Question 2?",
        ]
        agent.stock_ticker_service.get_stock_tickers.return_value = (
            getStockTickersResponse(
                success=True,
                response=[
                    StockTicker(
                        ticker="AAPL",
                        company_name="Apple",
                        explanation="",
                        instrument_type="equity",
                    ),
                    StockTicker(
                        ticker="GOOGL",
                        company_name="Google",
                        explanation="",
                        instrument_type="equity",
                    ),
                    StockTicker(
                        ticker="MSFT",
                        company_name="Microsoft",
                        explanation="",
                        instrument_type="equity",
                    ),
                ],
            )
        )

        result = await agent._handle_no_tool_calls()

        assert result is True
        agent.logger.info.assert_called_with("Response is satisfactory.")
        agent.follow_up_question_service.append_suggested_question_to_message.assert_called_once()
        agent.stock_ticker_service.append_stock_diagram_to_message.assert_called_once()
        agent.chat_service.modify_assistant_message.assert_called_once()
        assert agent.review_steps == 0

    @pytest.mark.asyncio
    async def test_handle_no_tool_calls_failed_evaluation(
        self, configured_search_agent
    ):
        """Test handling when evaluation fails."""
        agent = configured_search_agent
        agent._tool_evaluation_check_list = ["hallucination"]
        agent.config.follow_up_questions_config.number_of_follow_up_questions = 2
        agent.config.stock_ticker_config.enabled = True

        # Configure mock returns
        agent.evaluation_service.run_evaluation_of_streaming_result.return_value = [
            EvaluationMetricResult(
                name=EvaluationMetricName.HALLUCINATION,
                value="HIGH",  # loop_history, evaluation_result_passed
                reason="",
                is_positive=False,
            )
        ]
        agent.follow_up_question_service.get_follow_up_question_suggestion.return_value = []
        agent.stock_ticker_service.get_stock_tickers.return_value = [
            getStockTickersResponse(
                success=True,
                response=[
                    StockTicker(
                        ticker="AAPL",
                        company_name="Apple",
                        explanation="",
                        instrument_type="equity",
                    ),
                    StockTicker(
                        ticker="GOOGL",
                        company_name="Google",
                        explanation="",
                        instrument_type="equity",
                    ),
                    StockTicker(
                        ticker="MSFT",
                        company_name="Microsoft",
                        explanation="",
                        instrument_type="equity",
                    ),
                ],
            ),
        ]

        result = await agent._handle_no_tool_calls()

        assert result is False
        agent.evaluation_service.inform_user_about_negative_evaluation.assert_called_once_with()
        assert (
            agent.review_steps == 1
        )  # Should increment for failed evaluation
        assert agent.evaluation_result_passed is True  # Should reset flag

    @pytest.mark.asyncio
    async def test_handle_no_tool_calls_without_follow_up_questions(
        self, configured_search_agent
    ):
        """Test handling when follow-up questions are disabled."""
        agent = configured_search_agent
        agent.config.follow_up_questions_config.number_of_follow_up_questions = 0

        # Configure mock returns
        agent.evaluation_service.run_evaluation_of_streaming_result.return_value = (
            [],
            True,  # loop_history, evaluation_passed
        )

        result = await agent._handle_no_tool_calls()

        assert result is True
        agent.follow_up_question_service.append_suggested_question_to_message.assert_not_called()


class TestHandleToolCalls:
    @pytest.fixture
    def mock_tool_calls(self):
        return [
            LanguageModelFunctionCall(
                id="test_id",
                function=LanguageModelFunction(
                    id="test_id",
                    name="test_tool",
                    arguments={"query": "test query"},
                ),
            )
        ]

    @pytest.fixture
    def mock_tool_chunks(self):
        return {"test_tool": ["chunk1", "chunk2"]}

    @pytest.fixture
    def configured_search_agent(self, search_agent):
        # Configure base agent with necessary mocks
        search_agent.loop_response = MagicMock()
        search_agent.loop_response.tool_calls = []
        search_agent.loop_response.message = MagicMock()
        search_agent.loop_response.message.text = "Initial message"

        # Mock the internal methods
        search_agent._create_new_assistant_message_if_loop_response_contains_content = MagicMock()
        search_agent._process_tool_calls = AsyncMock()

        return search_agent

    @pytest.mark.asyncio
    async def test_handle_tool_calls(
        self, configured_search_agent, mock_tool_calls, mock_tool_chunks
    ):
        """Test handling tool calls when there's initial message content."""
        agent = configured_search_agent
        agent.loop_response.message.text = "Some initial content"
        agent.loop_response.tool_calls = mock_tool_calls

        await agent._handle_tool_calls()

        # Should process tool calls
        agent._process_tool_calls.assert_called_once_with(
            tool_calls=mock_tool_calls
        )

    @pytest.mark.asyncio
    async def test_handle_tool_calls_with_none_tool_calls(
        self, configured_search_agent
    ):
        """Test handling when tool_calls is None (should raise AssertionError)."""
        agent = configured_search_agent
        agent.loop_response.tool_calls = None

        with pytest.raises(AssertionError):
            await agent._handle_tool_calls()

    @pytest.mark.asyncio
    async def test_handle_tool_calls_with_multiple_tools(
        self, configured_search_agent, mock_tool_chunks
    ):
        """Test handling multiple tool calls."""
        agent = configured_search_agent

        # Create multiple tool calls
        tool_calls = [
            LanguageModelFunction(
                name=InternalSearchTool.name,
                arguments={"search_string": "internal query"},
            ),
            LanguageModelFunction(
                name=WebSearchTool.name,
                arguments={"query": "web query"},
            ),
        ]

        agent.loop_response.tool_calls = tool_calls

        await agent._handle_tool_calls()

        # Should process all tool calls
        agent._process_tool_calls.assert_called_once_with(
            tool_calls=tool_calls
        )


class TestPromptGeneration:
    @pytest.fixture
    def configured_search_agent(self, search_agent):
        # Configure chat service
        search_agent.chat_service = MagicMock()
        search_agent.chat_service.modify_assistant_message = MagicMock()
        return search_agent

    @pytest.fixture
    def mock_tools(self):
        tool1 = MagicMock()
        tool1.name = "tool1"
        tool1.tool_description_for_system_prompt.return_value = (
            "Tool 1 description"
        )
        tool1.tool_format_information_for_system_prompt.return_value = (
            "Tool 1 format"
        )

        tool2 = MagicMock()
        tool2.name = "tool2"
        tool2.tool_description_for_system_prompt.return_value = (
            "Tool 2 description"
        )
        tool2.tool_format_information_for_system_prompt.return_value = (
            "Tool 2 format"
        )

        return [tool1, tool2]

    def test_get_user_message_for_plan_execution(
        self, configured_search_agent
    ):
        """Test generating user message for plan execution."""
        agent = configured_search_agent
        agent.event.payload.user_message.text = "test query"

        message = agent._get_user_message_for_plan_execution()

        assert isinstance(message, LanguageModelUserMessage)
        assert "test query" in message.content  # type: ignore

    def test_get_system_message_for_plan_execution(
        self, configured_search_agent, mock_tools
    ):
        """Test generating system message for plan execution."""
        agent = configured_search_agent
        agent.tools = mock_tools
        agent.agent_chunks_handler.chunks = []

        message = agent._get_system_message_for_plan_execution()

        assert isinstance(message, LanguageModelSystemMessage)
        assert datetime.now().date().isoformat() in message.content  # type: ignore
        for tool in mock_tools:
            tool.tool_description_for_system_prompt.assert_called()
            tool.tool_format_information_for_system_prompt.assert_called()

    def test_get_system_message_with_citation_appendix(
        self, configured_search_agent, mock_tools
    ):
        """Test system message generation with citation appendix when chunks exist."""
        agent = configured_search_agent
        agent.tools = mock_tools
        agent.agent_chunks_handler.chunks = [MagicMock()]  # Add a mock chunk

        message = agent._get_system_message_for_plan_execution()

        assert isinstance(message, LanguageModelSystemMessage)
        assert (
            SYSTEM_MESSAGE_TOOL_SELECTION_CITATION_APPENDIX in message.content
        )  # type: ignore

    def test_combine_user_and_system_message_with_history(
        self, configured_search_agent
    ):
        """Test combining messages with history."""
        agent = configured_search_agent

        # Setup test messages
        system_msg = LanguageModelSystemMessage(content="System message")
        user_msg = LanguageModelUserMessage(content="User message")
        agent.history = [
            LanguageModelUserMessage(content="History message 1"),
            LanguageModelAssistantMessage(content="History message 2"),
        ]
        agent._loop_history = [
            LanguageModelAssistantMessage(content="Loop history message")
        ]

        # Execute
        combined_messages = (
            agent._combine_user_and_system_message_with_history(
                system_msg, user_msg
            )
        )

        # Assert
        assert isinstance(combined_messages, LanguageModelMessages)
        assert (
            len(combined_messages.root) == 5
        )  # system + 2 history + user + 1 loop
        assert combined_messages.root[0] == system_msg
        assert combined_messages.root[-2] == user_msg
        assert combined_messages.root[-1].content == "Loop history message"
