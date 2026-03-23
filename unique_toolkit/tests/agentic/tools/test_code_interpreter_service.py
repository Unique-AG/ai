"""Tests for OpenAICodeInterpreterTool.get_debug_info."""

from typing import Any

import pytest
from openai.types.responses import ResponseCodeInterpreterToolCall

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service import (
    OpenAICodeInterpreterTool,
)


@pytest.fixture
def base_code_interpreter_call() -> ResponseCodeInterpreterToolCall:
    return ResponseCodeInterpreterToolCall(
        id="call-abc123",
        container_id="container-xyz789",
        status="completed",
        type="code_interpreter_call",
    )


@pytest.mark.ai
def test_get_debug_info__returns_id_and_container_id__for_completed_call(
    base_code_interpreter_call: ResponseCodeInterpreterToolCall,
) -> None:
    """
    Purpose: Verify get_debug_info extracts id and container_id from a ResponseCodeInterpreterToolCall.
    Why this matters: These fields are the core analytics data for code interpreter execution tracking.
    Setup summary: Build a completed call; assert returned dict contains id and container_id.
    """
    # Act
    result: dict[str, Any] = OpenAICodeInterpreterTool.get_debug_info(
        base_code_interpreter_call
    )

    # Assert
    assert result["id"] == "call-abc123"
    assert result["container_id"] == "container-xyz789"


@pytest.mark.ai
def test_get_debug_info__returns_only_expected_keys__for_any_call(
    base_code_interpreter_call: ResponseCodeInterpreterToolCall,
) -> None:
    """
    Purpose: Verify get_debug_info returns a dict with exactly the keys id and container_id.
    Why this matters: Extra keys would pollute analytics payloads downstream.
    Setup summary: Call get_debug_info; assert the result has exactly two keys.
    """
    # Act
    result: dict[str, Any] = OpenAICodeInterpreterTool.get_debug_info(
        base_code_interpreter_call
    )

    # Assert
    assert set(result.keys()) == {"id", "container_id"}


@pytest.mark.ai
@pytest.mark.parametrize(
    "call_id, container_id",
    [
        ("call-001", "container-001"),
        ("call-999", "container-abc"),
    ],
    ids=["first-call", "second-call"],
)
def test_get_debug_info__reflects_call_fields__for_different_calls(
    call_id: str, container_id: str
) -> None:
    """
    Purpose: Verify get_debug_info correctly maps id and container_id for varying inputs.
    Why this matters: Ensures no hardcoded values leak into debug output.
    Setup summary: Parametrized calls with distinct ids; assert each result mirrors its input.
    """
    # Arrange
    call = ResponseCodeInterpreterToolCall(
        id=call_id,
        container_id=container_id,
        status="completed",
        type="code_interpreter_call",
    )

    # Act
    result: dict[str, Any] = OpenAICodeInterpreterTool.get_debug_info(call)

    # Assert
    assert result["id"] == call_id
    assert result["container_id"] == container_id
