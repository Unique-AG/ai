from typing import Any
from unittest.mock import AsyncMock

import pytest

from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_manager._utils import (
    execute_tools_parallelized,
    filter_duplicate_tool_calls,
)
from unique_toolkit.language_model.schemas import LanguageModelFunction


@pytest.fixture
def base_tool_call() -> LanguageModelFunction:
    """Base tool call fixture for testing."""
    return LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test", "limit": 10},
    )


@pytest.fixture
def tool_call_with_dict_args() -> LanguageModelFunction:
    """Tool call with dictionary arguments."""
    return LanguageModelFunction(
        id="call-456",
        name="get_weather",
        arguments={"location": "New York", "units": "celsius"},
    )


@pytest.fixture
def tool_call_with_none_args() -> LanguageModelFunction:
    """Tool call with None arguments."""
    return LanguageModelFunction(
        id="call-789",
        name="list_all",
        arguments=None,
    )


@pytest.mark.ai
def test_filter_duplicate_tool_calls__returns_empty_list__when_input_empty() -> None:
    """
    Purpose: Verify function handles empty input list correctly.
    Why this matters: Edge case handling prevents runtime errors.
    Setup summary: Pass empty list, assert empty list returned.
    """
    # Arrange
    tool_calls: list[LanguageModelFunction] = []

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert result == []
    assert isinstance(result, list)


@pytest.mark.ai
def test_filter_duplicate_tool_calls__returns_single_call__when_no_duplicates(
    base_tool_call: LanguageModelFunction,
) -> None:
    """
    Purpose: Verify function returns single call when no duplicates exist.
    Why this matters: Ensures non-duplicate calls are preserved.
    Setup summary: Pass single tool call, assert same call returned.
    """
    # Arrange
    tool_calls = [base_tool_call]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] == base_tool_call


@pytest.mark.ai
def test_filter_duplicate_tool_calls__preserves_all__when_all_unique(
    base_tool_call: LanguageModelFunction,
    tool_call_with_dict_args: LanguageModelFunction,
    tool_call_with_none_args: LanguageModelFunction,
) -> None:
    """
    Purpose: Verify function preserves all calls when they are unique.
    Why this matters: Ensures valid tool calls are not incorrectly filtered.
    Setup summary: Pass three unique calls, assert all three returned.
    """
    # Arrange
    tool_calls = [base_tool_call, tool_call_with_dict_args, tool_call_with_none_args]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 3
    assert result[0] == base_tool_call
    assert result[1] == tool_call_with_dict_args
    assert result[2] == tool_call_with_none_args


@pytest.mark.ai
def test_filter_duplicate_tool_calls__removes_exact_duplicate__same_id_name_args() -> (
    None
):
    """
    Purpose: Verify function removes exact duplicate tool calls.
    Why this matters: Prevents duplicate tool execution in production.
    Setup summary: Create duplicate call with same id/name/args, assert only one returned.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test"},
    )
    call_2 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test"},
    )
    tool_calls = [call_1, call_2]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] == call_1


@pytest.mark.ai
def test_filter_duplicate_tool_calls__preserves_both__when_ids_differ() -> None:
    """
    Purpose: Verify function treats calls with different IDs as unique.
    Why this matters: IDs are part of equality check and must be preserved.
    Setup summary: Create calls with same name/args but different IDs, assert both kept.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test"},
    )
    call_2 = LanguageModelFunction(
        id="call-456",
        name="search",
        arguments={"query": "test"},
    )
    tool_calls = [call_1, call_2]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 2
    assert result[0] == call_1
    assert result[1] == call_2


@pytest.mark.ai
def test_filter_duplicate_tool_calls__preserves_both__when_names_differ() -> None:
    """
    Purpose: Verify function treats calls with different names as unique.
    Why this matters: Tool names determine behavior and must be distinguished.
    Setup summary: Create calls with same id/args but different names, assert both kept.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test"},
    )
    call_2 = LanguageModelFunction(
        id="call-123",
        name="get_weather",
        arguments={"query": "test"},
    )
    tool_calls = [call_1, call_2]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 2
    assert result[0] == call_1
    assert result[1] == call_2


@pytest.mark.ai
def test_filter_duplicate_tool_calls__preserves_both__when_arguments_differ() -> None:
    """
    Purpose: Verify function treats calls with different arguments as unique.
    Why this matters: Different arguments produce different results.
    Setup summary: Create calls with same id/name but different args, assert both kept.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test"},
    )
    call_2 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "different"},
    )
    tool_calls = [call_1, call_2]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 2
    assert result[0] == call_1
    assert result[1] == call_2


@pytest.mark.ai
def test_filter_duplicate_tool_calls__keeps_first_occurrence__when_multiple_duplicates() -> (
    None
):
    """
    Purpose: Verify function keeps first occurrence and removes subsequent duplicates.
    Why this matters: Consistent behavior for duplicate removal order.
    Setup summary: Create three identical calls, assert only first is kept.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test"},
    )
    call_2 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test"},
    )
    call_3 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test"},
    )
    tool_calls = [call_1, call_2, call_3]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] == call_1


@pytest.mark.ai
def test_filter_duplicate_tool_calls__preserves_order__with_mixed_duplicates() -> None:
    """
    Purpose: Verify function preserves original order while removing duplicates.
    Why this matters: Tool execution order can affect outcomes.
    Setup summary: Mix unique and duplicate calls, assert order and correct filtering.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-1",
        name="search",
        arguments={"query": "first"},
    )
    call_2 = LanguageModelFunction(
        id="call-2",
        name="get_weather",
        arguments={"location": "NYC"},
    )
    call_3 = LanguageModelFunction(
        id="call-1",
        name="search",
        arguments={"query": "first"},
    )
    call_4 = LanguageModelFunction(
        id="call-3",
        name="translate",
        arguments={"text": "hello"},
    )
    tool_calls = [call_1, call_2, call_3, call_4]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 3
    assert result[0] == call_1
    assert result[1] == call_2
    assert result[2] == call_4


@pytest.mark.ai
def test_filter_duplicate_tool_calls__handles_none_arguments__correctly() -> None:
    """
    Purpose: Verify function correctly handles tool calls with None arguments.
    Why this matters: Some tools don't require arguments and None is valid.
    Setup summary: Create duplicate calls with None arguments, assert deduplication works.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-123",
        name="list_all",
        arguments=None,
    )
    call_2 = LanguageModelFunction(
        id="call-123",
        name="list_all",
        arguments=None,
    )
    tool_calls = [call_1, call_2]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] == call_1
    assert result[0].arguments is None


@pytest.mark.ai
def test_filter_duplicate_tool_calls__handles_empty_dict_arguments__correctly() -> None:
    """
    Purpose: Verify function correctly handles tool calls with empty dict arguments.
    Why this matters: Empty dicts are different from None and should be handled correctly.
    Setup summary: Create duplicate calls with empty dict args, assert deduplication works.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-123",
        name="list_all",
        arguments={},
    )
    call_2 = LanguageModelFunction(
        id="call-123",
        name="list_all",
        arguments={},
    )
    tool_calls = [call_1, call_2]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] == call_1
    assert result[0].arguments == {}


@pytest.mark.ai
def test_filter_duplicate_tool_calls__distinguishes_none_from_empty_dict() -> None:
    """
    Purpose: Verify function treats None arguments differently from empty dict.
    Why this matters: None and {} have different semantic meanings.
    Setup summary: Create calls with None vs empty dict, assert both kept.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-123",
        name="list_all",
        arguments=None,
    )
    call_2 = LanguageModelFunction(
        id="call-123",
        name="list_all",
        arguments={},
    )
    tool_calls = [call_1, call_2]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 2
    assert result[0].arguments is None
    assert result[1].arguments == {}


@pytest.mark.ai
def test_filter_duplicate_tool_calls__handles_complex_nested_arguments() -> None:
    """
    Purpose: Verify function correctly handles deeply nested argument structures.
    Why this matters: Tool arguments can be complex nested objects.
    Setup summary: Create duplicate calls with nested dicts/lists, assert deduplication works.
    """
    # Arrange
    complex_args: dict[str, Any] = {
        "query": "test",
        "filters": {"date_range": {"start": "2024-01-01", "end": "2024-12-31"}},
        "options": ["sort", "limit"],
        "metadata": {"user": "test", "version": 1},
    }
    call_1 = LanguageModelFunction(
        id="call-123",
        name="advanced_search",
        arguments=complex_args,
    )
    call_2 = LanguageModelFunction(
        id="call-123",
        name="advanced_search",
        arguments=complex_args,
    )
    tool_calls = [call_1, call_2]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] == call_1


@pytest.mark.ai
@pytest.mark.parametrize(
    "duplicate_count",
    [2, 3, 5, 10],
    ids=["two-duplicates", "three-duplicates", "five-duplicates", "ten-duplicates"],
)
def test_filter_duplicate_tool_calls__handles_various_duplicate_counts(
    duplicate_count: int,
) -> None:
    """
    Purpose: Verify function handles various numbers of duplicates correctly.
    Why this matters: Ensures scalability for different duplicate scenarios.
    Setup summary: Parametrized test with different duplicate counts.
    """
    # Arrange
    base_call = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test"},
    )
    tool_calls = [base_call] * duplicate_count

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] == base_call


@pytest.mark.ai
def test_filter_duplicate_tool_calls__preserves_reference_identity__for_kept_calls(
    base_tool_call: LanguageModelFunction,
) -> None:
    """
    Purpose: Verify function returns the exact same object instances for kept calls.
    Why this matters: Ensures no unnecessary object copying, preserving identity.
    Setup summary: Pass tool call, verify returned object is same instance.
    """
    # Arrange
    tool_calls = [base_tool_call]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] is base_tool_call


@pytest.mark.ai
def test_filter_duplicate_tool_calls__deduplicates_by_content__not_reference() -> None:
    """
    Purpose: Verify function deduplicates based on argument content, not object identity.
    Why this matters: Ensures value-based comparison works even when dict objects differ.
    Setup summary: Create separate dict objects with identical content, assert deduplication works.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test", "limit": 10},
    )
    call_2 = LanguageModelFunction(
        id="call-123",
        name="search",
        arguments={"query": "test", "limit": 10},  # New dict, same content
    )
    tool_calls = [call_1, call_2]

    # Act
    result = filter_duplicate_tool_calls(tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] == call_1
    # Verify the arguments are equal by value even if different objects
    assert call_1.arguments is not call_2.arguments
    assert call_1.arguments == call_2.arguments


# ==================== Tests for execute_tools_parallelized ====================


@pytest.fixture
def mock_tool(mocker) -> Tool:
    """Create a mock tool for testing."""
    tool = mocker.AsyncMock(spec=Tool)
    tool.name = "search_tool"
    return tool


@pytest.fixture
def mock_tool_2(mocker) -> Tool:
    """Create a second mock tool for testing."""
    tool = mocker.AsyncMock(spec=Tool)
    tool.name = "weather_tool"
    return tool


@pytest.fixture
def successful_tool_response() -> ToolCallResponse:
    """Create a successful tool response."""
    return ToolCallResponse(
        id="call-123",
        name="search_tool",
        content="Search results here",
        error_message="",
    )


@pytest.fixture
def error_tool_response() -> ToolCallResponse:
    """Create an error tool response."""
    return ToolCallResponse(
        id="call-456",
        name="failing_tool",
        content="",
        error_message="Tool execution failed",
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__returns_empty_list__when_no_tool_calls() -> (
    None
):
    """
    Purpose: Verify function handles empty tool calls list correctly.
    Why this matters: Edge case handling prevents runtime errors.
    Setup summary: Pass empty tool calls and empty tools, assert empty list returned.
    """
    # Arrange
    tools: list[Tool] = []
    tool_calls: list[LanguageModelFunction] = []

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert result == []
    assert isinstance(result, list)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__executes_single_tool__successfully(
    mock_tool: Tool,
    base_tool_call: LanguageModelFunction,
    successful_tool_response: ToolCallResponse,
) -> None:
    """
    Purpose: Verify function executes a single tool call successfully.
    Why this matters: Core functionality for tool execution.
    Setup summary: Mock tool to return successful response, assert response returned.
    """
    # Arrange
    mock_tool.name = base_tool_call.name
    mock_tool.run = AsyncMock(return_value=successful_tool_response)
    tools = [mock_tool]
    tool_calls = [base_tool_call]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] == successful_tool_response
    mock_tool.run.assert_called_once_with(tool_call=base_tool_call)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__executes_multiple_tools__in_parallel(
    mock_tool: Tool,
    mock_tool_2: Tool,
) -> None:
    """
    Purpose: Verify function executes multiple tools in parallel.
    Why this matters: Parallel execution improves performance.
    Setup summary: Create multiple tools and calls, verify all executed and returned.
    """
    # Arrange
    call_1 = LanguageModelFunction(id="call-1", name="search_tool", arguments={})
    call_2 = LanguageModelFunction(id="call-2", name="weather_tool", arguments={})

    response_1 = ToolCallResponse(
        id="call-1", name="search_tool", content="Search result"
    )
    response_2 = ToolCallResponse(
        id="call-2", name="weather_tool", content="Weather data"
    )

    mock_tool.name = "search_tool"
    mock_tool.run = AsyncMock(return_value=response_1)
    mock_tool_2.name = "weather_tool"
    mock_tool_2.run = AsyncMock(return_value=response_2)

    tools = [mock_tool, mock_tool_2]
    tool_calls = [call_1, call_2]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 2
    assert result[0] == response_1
    assert result[1] == response_2
    mock_tool.run.assert_called_once_with(tool_call=call_1)
    mock_tool_2.run.assert_called_once_with(tool_call=call_2)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__returns_error_response__when_tool_not_found() -> (
    None
):
    """
    Purpose: Verify function returns error response when tool is not found.
    Why this matters: Graceful handling of missing tools prevents crashes.
    Setup summary: Call non-existent tool, assert error response returned.
    """
    # Arrange
    tool_call = LanguageModelFunction(
        id="call-123", name="non_existent_tool", arguments={}
    )
    tools: list[Tool] = []
    tool_calls = [tool_call]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0].id == "call-123"
    assert result[0].name == "non_existent_tool"
    assert "not found" in result[0].error_message.lower()
    assert not result[0].successful


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__handles_tool_exception__with_error_response(
    mock_tool: Tool,
) -> None:
    """
    Purpose: Verify function handles tool exceptions and returns error response.
    Why this matters: Exception handling prevents system crashes during tool execution.
    Setup summary: Mock tool to raise exception, assert error response with exception message.
    """
    # Arrange
    tool_call = LanguageModelFunction(id="call-123", name="search_tool", arguments={})
    mock_tool.name = "search_tool"
    mock_tool.run = AsyncMock(side_effect=ValueError("Invalid query"))

    tools = [mock_tool]
    tool_calls = [tool_call]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0].id == "call-123"
    assert result[0].name == "search_tool"
    assert "Invalid query" in result[0].error_message
    assert not result[0].successful


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__preserves_order__of_responses(
    mock_tool: Tool,
    mock_tool_2: Tool,
) -> None:
    """
    Purpose: Verify function preserves order of tool call responses.
    Why this matters: Response order may be important for downstream processing.
    Setup summary: Execute multiple tools, verify responses match call order.
    """
    # Arrange
    call_1 = LanguageModelFunction(id="call-1", name="search_tool", arguments={})
    call_2 = LanguageModelFunction(id="call-2", name="weather_tool", arguments={})
    call_3 = LanguageModelFunction(id="call-3", name="search_tool", arguments={})

    response_1 = ToolCallResponse(id="call-1", name="search_tool", content="Result 1")
    response_2 = ToolCallResponse(id="call-2", name="weather_tool", content="Result 2")
    response_3 = ToolCallResponse(id="call-3", name="search_tool", content="Result 3")

    mock_tool.name = "search_tool"
    # Use side_effect to return different responses for different calls
    mock_tool.run = AsyncMock(side_effect=[response_1, response_3])
    mock_tool_2.name = "weather_tool"
    mock_tool_2.run = AsyncMock(return_value=response_2)

    tools = [mock_tool, mock_tool_2]
    tool_calls = [call_1, call_2, call_3]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 3
    assert result[0].id == "call-1"
    assert result[1].id == "call-2"
    assert result[2].id == "call-3"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__executes_same_tool_multiple_times(
    mock_tool: Tool,
) -> None:
    """
    Purpose: Verify function can execute the same tool multiple times with different calls.
    Why this matters: Supports multiple invocations of the same tool.
    Setup summary: Create multiple calls to same tool, verify all executed.
    """
    # Arrange
    call_1 = LanguageModelFunction(
        id="call-1", name="search_tool", arguments={"query": "first"}
    )
    call_2 = LanguageModelFunction(
        id="call-2", name="search_tool", arguments={"query": "second"}
    )

    response_1 = ToolCallResponse(
        id="call-1", name="search_tool", content="First result"
    )
    response_2 = ToolCallResponse(
        id="call-2", name="search_tool", content="Second result"
    )

    mock_tool.name = "search_tool"
    mock_tool.run = AsyncMock(side_effect=[response_1, response_2])

    tools = [mock_tool]
    tool_calls = [call_1, call_2]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 2
    assert result[0] == response_1
    assert result[1] == response_2
    assert mock_tool.run.call_count == 2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__handles_mixed_success_and_failure(
    mock_tool: Tool,
    mock_tool_2: Tool,
) -> None:
    """
    Purpose: Verify function handles mixed successful and failed tool executions.
    Why this matters: Partial failures should not prevent other tools from executing.
    Setup summary: Mock one tool to succeed and another to fail, verify both responses.
    """
    # Arrange
    call_1 = LanguageModelFunction(id="call-1", name="search_tool", arguments={})
    call_2 = LanguageModelFunction(id="call-2", name="weather_tool", arguments={})

    success_response = ToolCallResponse(
        id="call-1", name="search_tool", content="Success"
    )

    mock_tool.name = "search_tool"
    mock_tool.run = AsyncMock(return_value=success_response)
    mock_tool_2.name = "weather_tool"
    mock_tool_2.run = AsyncMock(side_effect=RuntimeError("Weather API down"))

    tools = [mock_tool, mock_tool_2]
    tool_calls = [call_1, call_2]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 2
    assert result[0].successful
    assert result[0].content == "Success"
    assert not result[1].successful
    assert "Weather API down" in result[1].error_message


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__includes_debug_info__when_log_exceptions_true(
    mock_tool: Tool,
) -> None:
    """
    Purpose: Verify function includes debug trace when log_exceptions_to_debug_info is True.
    Why this matters: Debug information helps troubleshooting production issues.
    Setup summary: Mock tool to raise exception with log_exceptions_to_debug_info=True.
    """
    # Arrange
    tool_call = LanguageModelFunction(id="call-123", name="search_tool", arguments={})
    mock_tool.name = "search_tool"
    mock_tool.run = AsyncMock(side_effect=ValueError("Test error"))

    tools = [mock_tool]
    tool_calls = [tool_call]

    # Act
    result = await execute_tools_parallelized(
        tools, tool_calls, log_exceptions_to_debug_info=True
    )

    # Assert
    assert len(result) == 1
    assert not result[0].successful
    assert result[0].debug_info is not None
    assert "error_trace" in result[0].debug_info
    assert "ValueError" in result[0].debug_info["error_trace"]
    assert "Test error" in result[0].debug_info["error_trace"]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__excludes_debug_info__when_log_exceptions_false(
    mock_tool: Tool,
) -> None:
    """
    Purpose: Verify function excludes debug trace when log_exceptions_to_debug_info is False.
    Why this matters: Allows controlling debug information verbosity.
    Setup summary: Mock tool to raise exception with log_exceptions_to_debug_info=False.
    """
    # Arrange
    tool_call = LanguageModelFunction(id="call-123", name="search_tool", arguments={})
    mock_tool.name = "search_tool"
    mock_tool.run = AsyncMock(side_effect=ValueError("Test error"))

    tools = [mock_tool]
    tool_calls = [tool_call]

    # Act
    result = await execute_tools_parallelized(
        tools, tool_calls, log_exceptions_to_debug_info=False
    )

    # Assert
    assert len(result) == 1
    assert not result[0].successful
    # Debug info may be None or may not contain error_trace
    if result[0].debug_info is not None:
        assert "error_trace" not in result[0].debug_info


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__handles_empty_arguments__correctly(
    mock_tool: Tool,
) -> None:
    """
    Purpose: Verify function handles tool calls with None or empty arguments.
    Why this matters: Some tools don't require arguments.
    Setup summary: Create calls with None and empty dict args, verify execution.
    """
    # Arrange
    call_1 = LanguageModelFunction(id="call-1", name="search_tool", arguments=None)
    call_2 = LanguageModelFunction(id="call-2", name="search_tool", arguments={})

    response_1 = ToolCallResponse(id="call-1", name="search_tool", content="Result 1")
    response_2 = ToolCallResponse(id="call-2", name="search_tool", content="Result 2")

    mock_tool.name = "search_tool"
    mock_tool.run = AsyncMock(side_effect=[response_1, response_2])

    tools = [mock_tool]
    tool_calls = [call_1, call_2]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 2
    assert result[0] == response_1
    assert result[1] == response_2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__handles_complex_arguments__correctly(
    mock_tool: Tool,
) -> None:
    """
    Purpose: Verify function handles tool calls with complex nested arguments.
    Why this matters: Tool arguments can contain complex data structures.
    Setup summary: Create call with nested dict/list args, verify passed correctly.
    """
    # Arrange
    complex_args: dict[str, Any] = {
        "query": "test",
        "filters": {"date": {"start": "2024-01-01", "end": "2024-12-31"}},
        "options": ["sort", "limit"],
    }
    tool_call = LanguageModelFunction(
        id="call-123", name="search_tool", arguments=complex_args
    )
    response = ToolCallResponse(id="call-123", name="search_tool", content="Result")

    mock_tool.name = "search_tool"
    mock_tool.run = AsyncMock(return_value=response)

    tools = [mock_tool]
    tool_calls = [tool_call]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 1
    assert result[0] == response
    mock_tool.run.assert_called_once_with(tool_call=tool_call)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__creates_tools_by_name_dict__correctly(
    mock_tool: Tool,
    mock_tool_2: Tool,
) -> None:
    """
    Purpose: Verify function correctly maps tools by name for lookup.
    Why this matters: Efficient tool lookup by name is critical for performance.
    Setup summary: Provide multiple tools, verify correct tool executed for each call.
    """
    # Arrange
    call_1 = LanguageModelFunction(id="call-1", name="tool_b", arguments={})
    call_2 = LanguageModelFunction(id="call-2", name="tool_a", arguments={})

    response_1 = ToolCallResponse(id="call-1", name="tool_b", content="B result")
    response_2 = ToolCallResponse(id="call-2", name="tool_a", content="A result")

    mock_tool.name = "tool_a"
    mock_tool.run = AsyncMock(return_value=response_2)
    mock_tool_2.name = "tool_b"
    mock_tool_2.run = AsyncMock(return_value=response_1)

    # Provide tools in different order than calls
    tools = [mock_tool, mock_tool_2]
    tool_calls = [call_1, call_2]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 2
    assert result[0].name == "tool_b"
    assert result[1].name == "tool_a"
    mock_tool_2.run.assert_called_once_with(tool_call=call_1)
    mock_tool.run.assert_called_once_with(tool_call=call_2)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__handles_large_number_of_tools(
    mocker,
) -> None:
    """
    Purpose: Verify function scales with large number of parallel tool executions.
    Why this matters: Production systems may need to execute many tools simultaneously.
    Setup summary: Create 10 tools and calls, verify all execute correctly.
    """
    # Arrange
    tools = []
    tool_calls = []
    expected_responses = []

    for i in range(10):
        tool = mocker.AsyncMock(spec=Tool)
        tool.name = f"tool_{i}"
        response = ToolCallResponse(
            id=f"call-{i}", name=f"tool_{i}", content=f"Result {i}"
        )
        tool.run = AsyncMock(return_value=response)

        call = LanguageModelFunction(id=f"call-{i}", name=f"tool_{i}", arguments={})

        tools.append(tool)
        tool_calls.append(call)
        expected_responses.append(response)

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 10
    for i, response in enumerate(result):
        assert response.id == f"call-{i}"
        assert response.name == f"tool_{i}"
        assert response.content == f"Result {i}"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_execute_tools_parallelized__all_not_found__returns_all_errors() -> None:
    """
    Purpose: Verify function returns error for all calls when no tools available.
    Why this matters: Graceful handling when tool registry is empty or misconfigured.
    Setup summary: Call multiple non-existent tools, verify all return errors.
    """
    # Arrange
    call_1 = LanguageModelFunction(id="call-1", name="tool_a", arguments={})
    call_2 = LanguageModelFunction(id="call-2", name="tool_b", arguments={})
    call_3 = LanguageModelFunction(id="call-3", name="tool_c", arguments={})

    tools: list[Tool] = []
    tool_calls = [call_1, call_2, call_3]

    # Act
    result = await execute_tools_parallelized(tools, tool_calls)

    # Assert
    assert len(result) == 3
    for i, response in enumerate(result):
        assert not response.successful
        assert "not found" in response.error_message.lower()
        assert response.id == f"call-{i + 1}"
