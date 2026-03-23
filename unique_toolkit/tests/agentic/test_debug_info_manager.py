"""Tests for DebugInfoManager and _extract_tool_calls_from_stream_response."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from openai.types.responses import ResponseCodeInterpreterToolCall

from unique_toolkit.agentic.debug_info_manager.debug_info_manager import (
    DebugInfoManager,
    _extract_tool_calls_from_stream_response,
)
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageRole,
    LanguageModelStreamResponse,
    LanguageModelStreamResponseMessage,
    ResponsesLanguageModelStreamResponse,
)

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------


def _make_message() -> LanguageModelStreamResponseMessage:
    return LanguageModelStreamResponseMessage(
        id="msg-1",
        chat_id="chat-1",
        previous_message_id=None,
        role=LanguageModelMessageRole.ASSISTANT,
        text="hello",
    )


def _make_code_interpreter_call(
    call_id: str = "call-1",
    container_id: str = "container-1",
) -> ResponseCodeInterpreterToolCall:
    return ResponseCodeInterpreterToolCall(
        id=call_id,
        container_id=container_id,
        status="completed",
        type="code_interpreter_call",
    )


def _make_responses_stream_response(
    calls: list[ResponseCodeInterpreterToolCall],
) -> ResponsesLanguageModelStreamResponse:
    return ResponsesLanguageModelStreamResponse(
        message=_make_message(),
        output=calls,  # type: ignore[arg-type]
    )


@pytest.fixture
def debug_info_manager() -> DebugInfoManager:
    return DebugInfoManager()


@pytest.fixture
def tool_manager() -> MagicMock:
    mock = MagicMock()
    mock.get_exclusive_tools.return_value = []
    mock.get_tool_choices.return_value = []
    return mock


# ---------------------------------------------------------------------------
# _extract_tool_calls_from_stream_response
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__returns_empty__when_not_responses_stream(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify the helper returns an empty list for a plain LanguageModelStreamResponse.
    Why this matters: Only ResponsesLanguageModelStreamResponse carries code interpreter calls;
                      processing other types would raise attribute errors.
    Setup summary: Provide a base LanguageModelStreamResponse; assert empty list returned.
    """
    # Arrange
    stream_response = LanguageModelStreamResponse(
        message=_make_message(),
    )

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert result == []


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__returns_empty__when_no_code_interpreter_calls(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify the helper returns an empty list when the stream response has no code interpreter calls.
    Why this matters: Avoids polluting debug_info with empty or wrong entries.
    Setup summary: Build ResponsesLanguageModelStreamResponse with empty output; assert empty list.
    """
    # Arrange
    stream_response = _make_responses_stream_response(calls=[])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert result == []


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__returns_one_entry__for_single_call(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify the helper returns a single tool info dict for one code interpreter call.
    Why this matters: Each call must produce exactly one analytics entry with the correct structure.
    Setup summary: One code interpreter call; assert result has one entry with name and info.
    """
    # Arrange
    call = _make_code_interpreter_call(call_id="call-1", container_id="ctr-1")
    stream_response = _make_responses_stream_response(calls=[call])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert len(result) == 1
    assert result[0]["name"] == OpenAIBuiltInToolName.CODE_INTERPRETER
    assert result[0]["info"]["id"] == "call-1"
    assert result[0]["info"]["container_id"] == "ctr-1"


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__deduplicates_calls__with_same_id(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify duplicate code interpreter calls (same id) are deduplicated to one entry.
    Why this matters: Streaming can produce repeated events for the same call; counting them
                      twice would corrupt analytics.
    Setup summary: Two calls with identical id in output; assert only one entry returned.
    """
    # Arrange
    call_a = _make_code_interpreter_call(call_id="call-dup", container_id="ctr-1")
    call_b = _make_code_interpreter_call(call_id="call-dup", container_id="ctr-1")
    stream_response = _make_responses_stream_response(calls=[call_a, call_b])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert len(result) == 1
    assert result[0]["info"]["id"] == "call-dup"


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__returns_multiple_entries__for_distinct_calls(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify two distinct code interpreter calls produce two separate tool info entries.
    Why this matters: Multiple code blocks in one response must each be tracked individually.
    Setup summary: Two calls with different ids; assert two entries returned in order.
    """
    # Arrange
    call_a = _make_code_interpreter_call(call_id="call-1", container_id="ctr-1")
    call_b = _make_code_interpreter_call(call_id="call-2", container_id="ctr-2")
    stream_response = _make_responses_stream_response(calls=[call_a, call_b])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert len(result) == 2
    ids = [entry["info"]["id"] for entry in result]
    assert "call-1" in ids
    assert "call-2" in ids


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__includes_loop_iteration__when_provided(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify loop_iteration is set in the info dict when a non-None index is passed.
    Why this matters: Loop iteration tracking is critical for multi-step agentic analytics.
    Setup summary: One call, loop_iteration_index=3; assert info contains loop_iteration=3.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager, loop_iteration_index=3
    )

    # Assert
    assert result[0]["info"]["loop_iteration"] == 3


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__omits_loop_iteration_key__when_not_provided(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify loop_iteration key is absent from info when loop_iteration_index is None.
    Why this matters: Matches the behaviour of extract_tool_debug_info, which only sets the key
                      when a non-None index is given, so downstream consumers checking for key
                      presence behave consistently across both regular and builtin tool entries.
    Setup summary: One call, no loop_iteration_index; assert loop_iteration key is absent.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])

    # Act
    result: list[dict[str, Any]] = _extract_tool_calls_from_stream_response(
        stream_response, tool_manager
    )

    # Assert
    assert "loop_iteration" not in result[0]["info"]


# ---------------------------------------------------------------------------
# DebugInfoManager.extract_builtin_tool_debug_info
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_debug_info_manager__extract_builtin_tool_debug_info__extends_tools_list(
    debug_info_manager: DebugInfoManager,
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify extract_builtin_tool_debug_info appends code interpreter entries to debug_info tools.
    Why this matters: The manager is the single accumulation point for all debug analytics.
    Setup summary: Manager starts empty; call method with one call; assert tools list has one entry.
    """
    # Arrange
    call = _make_code_interpreter_call(call_id="call-1", container_id="ctr-1")
    stream_response = _make_responses_stream_response(calls=[call])

    # Act
    debug_info_manager.extract_builtin_tool_debug_info(stream_response, tool_manager)

    # Assert
    tools: list[dict[str, Any]] = debug_info_manager.get()["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == OpenAIBuiltInToolName.CODE_INTERPRETER
    assert tools[0]["info"]["id"] == "call-1"
    assert tools[0]["info"]["container_id"] == "ctr-1"


@pytest.mark.ai
def test_debug_info_manager__extract_builtin_tool_debug_info__skips_non_responses_stream(
    debug_info_manager: DebugInfoManager,
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify no entries are added to tools when the stream is a plain LanguageModelStreamResponse.
    Why this matters: Calling this method with a non-Responses stream must be a no-op, not an error.
    Setup summary: Pass a base LanguageModelStreamResponse; assert tools list remains empty.
    """
    # Arrange
    stream_response = LanguageModelStreamResponse(message=_make_message())

    # Act
    debug_info_manager.extract_builtin_tool_debug_info(stream_response, tool_manager)

    # Assert
    assert debug_info_manager.get()["tools"] == []


@pytest.mark.ai
def test_debug_info_manager__extract_builtin_tool_debug_info__accumulates_across_calls(
    debug_info_manager: DebugInfoManager,
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify multiple invocations of extract_builtin_tool_debug_info accumulate entries.
    Why this matters: In multi-iteration loops each iteration appends its calls; total must be correct.
    Setup summary: Call method twice with one call each; assert tools list has two entries total.
    """
    # Arrange
    call_a = _make_code_interpreter_call(call_id="call-1", container_id="ctr-1")
    call_b = _make_code_interpreter_call(call_id="call-2", container_id="ctr-2")
    stream_a = _make_responses_stream_response(calls=[call_a])
    stream_b = _make_responses_stream_response(calls=[call_b])

    # Act
    debug_info_manager.extract_builtin_tool_debug_info(
        stream_a, tool_manager, loop_iteration_index=0
    )
    debug_info_manager.extract_builtin_tool_debug_info(
        stream_b, tool_manager, loop_iteration_index=1
    )

    # Assert
    tools: list[dict[str, Any]] = debug_info_manager.get()["tools"]
    assert len(tools) == 2
    assert tools[0]["info"]["loop_iteration"] == 0
    assert tools[1]["info"]["loop_iteration"] == 1


@pytest.mark.ai
def test_debug_info_manager__extract_builtin_tool_debug_info__passes_loop_iteration_to_entries(
    debug_info_manager: DebugInfoManager,
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify loop_iteration_index is propagated into each tool entry's info dict.
    Why this matters: Correct loop attribution is required for per-iteration agentic analytics.
    Setup summary: Call method with loop_iteration_index=5; assert info contains loop_iteration=5.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])

    # Act
    debug_info_manager.extract_builtin_tool_debug_info(
        stream_response, tool_manager, loop_iteration_index=5
    )

    # Assert
    tools: list[dict[str, Any]] = debug_info_manager.get()["tools"]
    assert tools[0]["info"]["loop_iteration"] == 5


# ---------------------------------------------------------------------------
# is_exclusive / is_forced flags (new in this branch)
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__is_exclusive_false__when_not_in_exclusive_tools(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify is_exclusive is False when CODE_INTERPRETER is not in get_exclusive_tools().
    Why this matters: Incorrect True would misrepresent the tool's exclusivity to downstream consumers.
    Setup summary: tool_manager returns empty exclusive list; assert is_exclusive=False on entry.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])
    tool_manager.get_exclusive_tools.return_value = []

    # Act
    result = _extract_tool_calls_from_stream_response(stream_response, tool_manager)

    # Assert
    assert result[0]["is_exclusive"] is False


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__is_exclusive_true__when_in_exclusive_tools(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify is_exclusive is True when CODE_INTERPRETER is returned by get_exclusive_tools().
    Why this matters: The flag must accurately reflect whether the tool was configured as exclusive.
    Setup summary: tool_manager returns [CODE_INTERPRETER] from get_exclusive_tools(); assert is_exclusive=True.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])
    tool_manager.get_exclusive_tools.return_value = [
        OpenAIBuiltInToolName.CODE_INTERPRETER
    ]

    # Act
    result = _extract_tool_calls_from_stream_response(stream_response, tool_manager)

    # Assert
    assert result[0]["is_exclusive"] is True


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__is_forced_false__when_not_in_tool_choices(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify is_forced is False when CODE_INTERPRETER is not in get_tool_choices().
    Why this matters: Incorrect True would misrepresent whether the tool was force-selected.
    Setup summary: tool_manager returns empty tool_choices list; assert is_forced=False on entry.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])
    tool_manager.get_tool_choices.return_value = []

    # Act
    result = _extract_tool_calls_from_stream_response(stream_response, tool_manager)

    # Assert
    assert result[0]["is_forced"] is False


@pytest.mark.ai
def test_extract_tool_calls_from_stream_response__is_forced_true__when_in_tool_choices(
    tool_manager: MagicMock,
) -> None:
    """
    Purpose: Verify is_forced is True when CODE_INTERPRETER is returned by get_tool_choices().
    Why this matters: The flag must accurately reflect whether the tool was force-selected by the caller.
    Setup summary: tool_manager returns [CODE_INTERPRETER] from get_tool_choices(); assert is_forced=True.
    """
    # Arrange
    call = _make_code_interpreter_call()
    stream_response = _make_responses_stream_response(calls=[call])
    tool_manager.get_tool_choices.return_value = [
        OpenAIBuiltInToolName.CODE_INTERPRETER
    ]

    # Act
    result = _extract_tool_calls_from_stream_response(stream_response, tool_manager)

    # Assert
    assert result[0]["is_forced"] is True
