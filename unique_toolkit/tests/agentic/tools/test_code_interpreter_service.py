"""Tests for OpenAICodeInterpreterTool (get_debug_info, get_required_include_params)."""

from typing import Any
from unittest.mock import MagicMock, patch

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
    assert set(result.keys()) == {"id", "container_id", "code"}


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


# ============================================================================
# Tests for get_required_include_params
# ============================================================================

_SERVICE_FF_PATH = (
    "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service.feature_flags"
)


def _make_tool(company_id: str = "company-1") -> OpenAICodeInterpreterTool:
    """Construct a minimal OpenAICodeInterpreterTool instance (auto container, no container_id needed)."""
    config = MagicMock()
    config.use_auto_container = True
    return OpenAICodeInterpreterTool(
        config=config, container_id=None, company_id=company_id
    )


@pytest.mark.ai
def test_get_required_include_params__returns_code_interpreter_outputs__when_ff_on() -> (
    None
):
    """
    Purpose: Verify get_required_include_params returns ["code_interpreter_call.outputs"] when
    enable_code_execution_fence_un_17972 is on for the tool's company.
    Why this matters: The include param is what causes OpenAI to attach execution logs to the
    response; without it the postprocessor falls back to source code only.
    """
    mock_ff = MagicMock()
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = True

    with patch(_SERVICE_FF_PATH, mock_ff):
        tool = _make_tool(company_id="company-ff-on")
        result = tool.get_required_include_params()

    assert result == ["code_interpreter_call.outputs"]
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.assert_called_once_with(
        "company-ff-on"
    )


@pytest.mark.ai
def test_get_required_include_params__returns_empty_list__when_ff_off() -> None:
    """
    Purpose: Verify get_required_include_params returns [] when the fence FF is off.
    Why this matters: When FF is off, no extra include should be forwarded to the Responses API,
    preserving legacy behaviour exactly.
    """
    mock_ff = MagicMock()
    mock_ff.enable_code_execution_fence_un_17972.is_enabled.return_value = False

    with patch(_SERVICE_FF_PATH, mock_ff):
        tool = _make_tool(company_id="company-ff-off")
        result = tool.get_required_include_params()

    assert result == []
