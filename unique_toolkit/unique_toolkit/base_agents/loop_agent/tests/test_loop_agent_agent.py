from logging import Logger
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model import LanguageModelTokenLimits
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelFunctionCall,
    LanguageModelMessage,
    LanguageModelMessageRole,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
    LanguageModelToolMessage,
)
from unique_toolkit.base_agents.loop_agent.agent import LoopAgent
from unique_toolkit.base_agents.loop_agent.config import (
    LoopAgentConfig,
    LoopConfiguration,
)
from unique_toolkit.tools.schemas import ToolCallResponse
from unique_toolkit.tools.tool import Tool


@pytest.fixture
def mock_config():
    config = MagicMock(spec=LoopAgentConfig)
    config.language_model = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_1120
    )
    config.temperature = 0.0
    config.percent_of_max_tokens_for_history = 0.2
    config.max_history_tokens = 3000
    config.max_loop_iterations = 8
    config.token_limits = MagicMock(spec=LanguageModelTokenLimits)
    config.token_limits.max_history_tokens = 1000
    config.thinking_steps_display = False
    config.additional_llm_options = {}
    config.max_loop_iterations = 8
    config.loop_configuration = MagicMock(spec=LoopConfiguration)
    config.loop_configuration.max_tool_calls_per_iteration = 10
    return config


@pytest.fixture
def mock_logger():
    return MagicMock(spec=Logger)


@pytest.fixture
def mock_event():
    event = MagicMock(spec=ChatEvent)
    event.payload = MagicMock()
    event.payload.user_message = MagicMock()
    event.payload.user_message.text = "Test query"
    event.user_id = "user_0"
    event.company_id = "company_0"
    return event


@pytest.fixture
def mock_stream_response_no_tool_calls():
    response = MagicMock(spec=LanguageModelStreamResponse)
    response.tool_calls = None
    response.message = LanguageModelStreamResponseMessage(
        id="1",
        previous_message_id="0",
        role=LanguageModelMessageRole.ASSISTANT,
        text="Test response",
        original_text="Test response",
        references=[],
    )
    return response


@pytest.fixture
def mock_content_chunk_list():
    return [
        ContentChunk(
            id="c_0",
            text="Source 0",
            order=0,
        ),
        ContentChunk(
            id="c_1",
            text="Source 1",
            order=0,
        ),
    ]


class TestAgent(LoopAgent):
    def _compose_message_plan_execution(self):
        return MagicMock()

    async def _handle_no_tool_calls(self):
        return True

    async def _handle_tool_calls(self):
        pass


@pytest.fixture
def loop_agent(mock_event, mock_config):
    return TestAgent(
        event=mock_event,
        config=mock_config,
        tools=[],
        debug_info_manager=MagicMock(),
        agent_chunks_handler=MagicMock(),
    )


############################################################
### Init
############################################################
@pytest.mark.asyncio
async def test_loop_agent_initialization(loop_agent, mock_config):
    assert loop_agent.event is not None
    assert loop_agent.config is mock_config
    assert loop_agent.logger is not None
    assert loop_agent.chat_service is not None
    assert loop_agent.llm_service is not None
    assert loop_agent.agent_debug_info is not None
    assert loop_agent.agent_chunks_handler is not None
    assert len(loop_agent.tools) == len(mock_config.available_tools)
    assert loop_agent.tool_definitions is not None
    assert loop_agent._tools_used_in_loop == []
    assert loop_agent._tool_evaluation_check_list == []
    assert loop_agent._loop_history == []
    assert loop_agent._start_text == ""
    assert loop_agent.tool_call_result_history == []
    assert loop_agent.current_iteration_index == 0
    assert loop_agent.thinking_steps == ""
    assert loop_agent.thinking_step_number == 1
    assert loop_agent.tool_progress_reporter is not None


##############################
# Main loop
##############################
@pytest.mark.asyncio
@patch("_common.agents.loop_agent.agent.get_history")
async def test_loop_agent_run(
    mock_history, loop_agent, mock_stream_response_no_tool_calls
):
    mock_history.return_value = []
    loop_agent._plan_or_execute = AsyncMock(
        return_value=mock_stream_response_no_tool_calls
    )
    loop_agent.chat_service = AsyncMock()
    loop_agent._process_plan = AsyncMock(return_value=True)

    await loop_agent.run()

    mock_history.assert_called_once()
    loop_agent._plan_or_execute.assert_called_once()
    loop_agent._process_plan.assert_called_once()

    assert loop_agent.loop_response == mock_stream_response_no_tool_calls
    assert loop_agent._tools_used_in_loop == []


@pytest.mark.asyncio
async def test_plan_or_execute(loop_agent, mock_stream_response_no_tool_calls):
    # Mock the return values of the methods and attributes
    loop_agent._compose_message_plan_execution = MagicMock(
        return_value=["message1", "message2"]
    )
    loop_agent.agent_chunks_handler = MagicMock()
    loop_agent.agent_chunks_handler.chunks = ["chunk1", "chunk2"]
    loop_agent.start_text = "start_text"
    loop_agent.agent_debug_info.get = MagicMock(return_value={"debug": "info"})

    # Mock the llm_service.stream_complete method
    loop_agent.chat_service.stream_complete_async = AsyncMock(
        return_value=mock_stream_response_no_tool_calls
    )

    # Call the method
    result = await loop_agent._plan_or_execute()

    # Assert the result
    assert result == mock_stream_response_no_tool_calls

    # Verify that the methods were called with the expected arguments
    loop_agent._compose_message_plan_execution.assert_called_once()
    loop_agent.chat_service.stream_complete_async.assert_called_once_with(
        messages=["message1", "message2"],
        model_name=loop_agent.config.language_model.name,
        tools=[],
        content_chunks=["chunk1", "chunk2"],
        start_text="start_text",
        debug_info={"debug": "info"},
        temperature=0.0,
        other_options=loop_agent.config.additional_llm_options,
    )


@pytest.mark.asyncio
async def test_process_plan_no_response(loop_agent):
    loop_agent.chat_service = AsyncMock()

    # Test when loop_response is None
    loop_agent.loop_response = None

    result = await loop_agent._process_plan()

    loop_agent.chat_service.modify_assistant_message.assert_called_once_with(
        content="An error occurred. Please try again..."
    )
    assert result is True


@pytest.mark.asyncio
async def test_process_plan_no_tool_calls(
    loop_agent, mock_stream_response_no_tool_calls
):
    loop_agent.chat_service = AsyncMock()

    # Test when loop_response has no tool calls
    loop_agent.loop_response = mock_stream_response_no_tool_calls
    loop_agent._handle_no_tool_calls = AsyncMock(return_value=True)

    result = await loop_agent._process_plan()

    loop_agent._handle_no_tool_calls.assert_awaited_once()
    assert result is True


@pytest.mark.asyncio
async def test_process_plan_with_tool_calls(
    loop_agent, mock_stream_response_with_tool_calls
):
    loop_agent.chat_service = AsyncMock()

    # Test when loop_response has tool calls
    loop_agent.loop_response = mock_stream_response_with_tool_calls
    loop_agent._handle_tool_calls = AsyncMock()

    result = await loop_agent._process_plan()

    loop_agent._handle_tool_calls.assert_awaited_once()
    assert result is False


##############################
# Optional methods to override
##############################
def test_optional_initialization_step(loop_agent):
    try:
        # When calling the optional initialization step
        loop_agent._optional_initialization_step()
    except Exception as e:
        # Then it should not raise any exception
        pytest.fail(f"_optional_initialization_step raised an exception: {e}")


##############################
# Tool processing
##############################
@pytest.mark.asyncio
async def test_process_tool_calls(loop_agent):
    loop_agent._append_tool_calls_to_history = MagicMock()
    loop_agent._process_single_tool_call = AsyncMock()

    tool_calls = [
        LanguageModelFunction(
            id="id_1", name="Internal", arguments={"query": "Test query"}
        ),
        LanguageModelFunction(id="id_2", name="Web", arguments={"query": "Test query"}),
    ]

    await loop_agent._process_tool_calls(tool_calls)

    loop_agent._append_tool_calls_to_history.assert_called_once_with(tool_calls)
    calls = [call(tool_call=tool_call) for tool_call in tool_calls]
    loop_agent._process_single_tool_call.assert_has_awaits(calls, any_order=True)


def test_append_tool_calls_to_history(loop_agent):
    tool_calls = [
        LanguageModelFunction(
            id="id_1", name="Internal", arguments={"query": "Test query"}
        ),
        LanguageModelFunction(id="id_2", name="Web", arguments={"query": "Test query"}),
    ]
    tool_calls[0].id = "id_1"
    tool_calls[1].id = "id_2"

    # Call the method
    loop_agent._append_tool_calls_to_history(tool_calls)
    expected_assistant_message = [
        LanguageModelFunctionCall.create_assistant_message_from_tool_calls(
            tool_calls=tool_calls
        )
    ]

    assert loop_agent._loop_history == expected_assistant_message
    assert loop_agent._tools_used_in_loop == ["Internal", "Web"]


@pytest.mark.asyncio
async def test_process_single_tool_call(loop_agent, mock_content_chunk_list):
    loop_agent.agent_chunks_handler.tool_chunks = {}
    # Mock the methods and attributes that are called within _process_single_tool_call
    loop_agent.logger.info = MagicMock()
    loop_agent._get_tool_instance_by_name = MagicMock()

    # Create a mock tool instance and its methods
    mock_tool_instance = AsyncMock(spec=Tool)
    mock_tool_instance.run = AsyncMock(
        return_value=ToolCallResponse(
            id="id_1",
            name="InternalSearch",
            content_chunks=mock_content_chunk_list,
            debug_info={"debug_info": "debug_info"},
        )
    )

    loop_agent._get_tool_instance_by_name.return_value = mock_tool_instance

    # Create a mock tool call
    tool_call = LanguageModelFunction(
        id="id_1", name="InternalSearch", arguments={"query": "Test query"}
    )

    await loop_agent._process_single_tool_call(tool_call)

    loop_agent._get_tool_instance_by_name.assert_called_once_with(tool_call.name)
    mock_tool_instance.run.assert_called_with(tool_call=tool_call)


@patch("_common.agents.loop_agent.agent.LoopAgent._update_debug_info")
@patch("_common.agents.loop_agent.agent.LoopAgent._update_evaluation_checks")
@patch("_common.agents.loop_agent.agent.LoopAgent._manage_tool_chunks")
@patch("_common.agents.loop_agent.agent.LoopAgent._append_tool_call_result_to_history")
def test_handle_no_tool_call_results_with_valid_responses(
    mock_update_debug_info,
    mock_update_evaluation_checks,
    mock_manage_tool_chunks,
    mock_append_tool_call_result_to_history,
    loop_agent,
):
    loop_agent.logger.debug = MagicMock()
    mock_tool_call_results = [
        ToolCallResponse(
            id="1",
            name="valid_tool",
            content_chunks=[],
            debug_info={"key": "value"},
        ),
        ToolCallResponse(
            id="2",
            name="valid_tool",
            content_chunks=[],
            debug_info={"key2": "value2"},
        ),
    ]

    mock_tool_instance = AsyncMock(spec=Tool)
    loop_agent._get_tool_instance_by_name = MagicMock()
    loop_agent._get_tool_instance_by_name.return_value = mock_tool_instance

    loop_agent._handle_tool_call_results(mock_tool_call_results)

    assert loop_agent.logger.debug.call_count == 1
    assert mock_update_debug_info.call_count == 2
    assert mock_update_evaluation_checks.call_count == 2
    assert mock_manage_tool_chunks.call_count == 2
    assert mock_append_tool_call_result_to_history.call_count == 2


@patch("_common.agents.loop_agent.agent.LoopAgent._update_debug_info")
@patch("_common.agents.loop_agent.agent.LoopAgent._update_evaluation_checks")
@patch("_common.agents.loop_agent.agent.LoopAgent._manage_tool_chunks")
@patch("_common.agents.loop_agent.agent.LoopAgent._append_tool_call_result_to_history")
def test_handle_no_tool_call_results_with_none_responses(
    mock_update_debug_info,
    mock_update_evaluation_checks,
    mock_manage_tool_chunks,
    mock_append_tool_call_result_to_history,
    loop_agent,
):
    loop_agent.logger.debug = MagicMock()
    loop_agent.logger.warning = MagicMock()
    mock_tool_call_results = [None, None]

    loop_agent._handle_tool_call_results(mock_tool_call_results)

    assert loop_agent.logger.warning.call_count == 2
    assert mock_update_debug_info.call_count == 0
    assert mock_update_evaluation_checks.call_count == 0
    assert mock_manage_tool_chunks.call_count == 0
    assert mock_append_tool_call_result_to_history.call_count == 0


@patch("_common.agents.loop_agent.agent.LoopAgent._update_debug_info")
@patch("_common.agents.loop_agent.agent.LoopAgent._update_evaluation_checks")
@patch("_common.agents.loop_agent.agent.LoopAgent._manage_tool_chunks")
@patch("_common.agents.loop_agent.agent.LoopAgent._append_tool_call_result_to_history")
def test_handle_no_tool_call_results_with_valid_and_none_responses(
    mock_update_debug_info,
    mock_update_evaluation_checks,
    mock_manage_tool_chunks,
    mock_append_tool_call_result_to_history,
    loop_agent,
):
    loop_agent.logger.debug = MagicMock()
    loop_agent.logger.warning = MagicMock()
    mock_tool_call_results = [
        ToolCallResponse(
            id="1",
            name="valid_tool",
            content_chunks=[],
            debug_info={"key": "value"},
        ),
        None,
    ]

    mock_tool_instance = AsyncMock(spec=Tool)
    loop_agent._get_tool_instance_by_name = MagicMock()
    loop_agent._get_tool_instance_by_name.return_value = mock_tool_instance

    loop_agent._handle_tool_call_results(mock_tool_call_results)

    assert loop_agent.logger.warning.call_count == 1
    assert mock_update_debug_info.call_count == 1
    assert mock_update_evaluation_checks.call_count == 1
    assert mock_manage_tool_chunks.call_count == 1
    assert mock_append_tool_call_result_to_history.call_count == 1


def test_update_debug_info(loop_agent):
    tool_response = ToolCallResponse(id="1", name="test", debug_info={"test": "data"})

    loop_agent._update_debug_info(tool_response)
    loop_agent.agent_debug_info.tool.assert_called_once_with({"test": "data"})


def test_update_evaluation_checks_with_valid_tool(loop_agent):
    tool_response = ToolCallResponse(id="1", name="valid_tool")

    mock_tool_instance = AsyncMock(spec=Tool)
    mock_tool_instance.get_evaluation_checks_based_on_tool_response = MagicMock()
    mock_tool_instance.get_evaluation_checks_based_on_tool_response.return_value = [
        "check1",
        "check2",
    ]

    loop_agent._update_evaluation_checks(mock_tool_instance, tool_response)

    assert "check1" in loop_agent._tool_evaluation_check_list
    assert "check2" in loop_agent._tool_evaluation_check_list
    assert len(loop_agent._tool_evaluation_check_list) == 2


def test_manage_tool_chunks(loop_agent, mock_content_chunk_list):
    """Test managing tool chunks with and without content."""
    test_cases = [
        {
            "tool_response": ToolCallResponse(
                id="1",
                name="test_tool",
                content_chunks=mock_content_chunk_list,
            ),
            "expected_chunks_length": 1,
            "assert_extend_called": True,
        },
        {
            "tool_response": ToolCallResponse(
                id="2", name="test_tool", content_chunks=None
            ),
            "expected_chunks_length": 1,
            "assert_extend_called": False,
        },
    ]

    for case in test_cases:
        loop_agent.agent_chunks_handler.tool_chunks = {}
        loop_agent._manage_tool_chunks(case["tool_response"])

        assert (
            len(loop_agent.agent_chunks_handler.tool_chunks)
            == case["expected_chunks_length"]
        )
        assert loop_agent.agent_chunks_handler.tool_chunks[
            case["tool_response"].id
        ] == {
            "tool_name": case["tool_response"].name,
            "chunks": case["tool_response"].content_chunks or [],
        }
        if case["assert_extend_called"]:
            loop_agent.agent_chunks_handler.extend.assert_called_once_with(
                mock_content_chunk_list
            )


def test_append_tool_calls_to_history_none(loop_agent):
    # Call the method with None
    loop_agent._append_tool_calls_to_history(None)

    # Assert the loop history and tools used in loop remain empty
    assert loop_agent._loop_history == []
    assert loop_agent._tools_used_in_loop == []


@pytest.mark.asyncio
async def test_process_single_tool_call_no_tool_instance(loop_agent):
    loop_agent.agent_chunks_handler.tool_chunks = {}
    # Mock the methods and attributes that are called within _process_single_tool_call
    loop_agent._get_tool_instance_by_name = MagicMock(return_value=None)

    # Create a mock tool call
    tool_call = LanguageModelFunction(
        id="id_1", name="InternalSearch", arguments={"query": "Test query"}
    )
    tool_call.id = "id_1"

    # Call the method
    await loop_agent._process_single_tool_call(tool_call)

    # Assert _get_tool_instance_by_name was called with the correct tool name
    loop_agent._get_tool_instance_by_name.assert_called_once_with(tool_call.name)

    # # Assert that no further processing was done since tool_instance is None
    assert loop_agent._tool_evaluation_check_list == []
    assert loop_agent.agent_chunks_handler.tool_chunks == {}


def test_append_tool_call_result(loop_agent, mock_content_chunk_list):
    tool_response = ToolCallResponse(
        id="id_1",
        name="test",
        debug_info={"test": "data"},
        content_chunks=mock_content_chunk_list,
    )
    mock_tool_instance = AsyncMock(spec=Tool)
    mock_tool_instance.name = "test"
    mock_tool_instance.get_tool_call_result_for_loop_history = MagicMock(
        spec=LanguageModelMessage
    )
    mock_tool_instance.get_tool_call_result_for_loop_history.return_value = (
        LanguageModelToolMessage(
            content="sources in correct format",
            tool_call_id=tool_response.id,  # type: ignore
            name=tool_response.name,
        )
    )

    loop_agent._append_tool_call_result_to_history(mock_tool_instance, tool_response)

    assert len(loop_agent._loop_history) == 1
    assert loop_agent._loop_history[0].content == "sources in correct format"
    assert loop_agent._loop_history[0].tool_call_id == tool_response.id
    assert loop_agent._loop_history[0].name == tool_response.name


############################################################
### Thinking steps
############################################################
@pytest.mark.asyncio
async def test_update_thinking_steps_tool_call(
    loop_agent, mock_stream_response_no_tool_calls
):
    # Setup
    loop_agent.loop_response = mock_stream_response_no_tool_calls
    mock_stream_response_no_tool_calls.message.original_text = "Test thinking step"

    # Test first thinking step
    loop_agent._update_thinking_steps_tool_call()
    assert loop_agent.thinking_steps == "\n<i><b>Step 1:</b>\nTest thinking step</i>\n"
    assert loop_agent.thinking_step_number == 2
    assert loop_agent.start_text.startswith("<details open>")

    # Test subsequent thinking step
    loop_agent._update_thinking_steps_tool_call()
    assert loop_agent.thinking_steps.endswith(
        "\n\n<i><b>Step 2:</b>\nTest thinking step</i>\n\n"
    )
    assert loop_agent.thinking_step_number == 3


@pytest.mark.asyncio
async def test_close_thinking_steps_in_output(
    loop_agent, mock_stream_response_no_tool_calls
):
    # Setup
    loop_agent.thinking_steps = "Test thinking steps"
    loop_agent.loop_response = mock_stream_response_no_tool_calls
    loop_agent.loop_response.message.text = "<details open>Test content</details>"
    loop_agent.chat_service = AsyncMock()

    # Test
    loop_agent._close_thinking_steps_in_output()

    # Verify
    assert loop_agent.loop_response.message.text == "<details>Test content</details>"
    loop_agent.chat_service.modify_assistant_message.assert_called_once_with(
        content="<details>Test content</details>"
    )
