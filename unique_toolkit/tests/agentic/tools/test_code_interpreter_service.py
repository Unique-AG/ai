"""Tests for OpenAICodeInterpreterTool (get_debug_info, get_required_include_params, get_tool_prompts)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.responses import ResponseCodeInterpreterToolCall

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE,
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service import (
    CodeExecutionShortTermMemorySchema,
    OpenAICodeInterpreterTool,
    _upload_files_to_container,
)
from unique_toolkit.content.schemas import Content


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


def _auto_container_tool(
    config: OpenAICodeInterpreterConfig,
    company_id: str = "company-1",
) -> OpenAICodeInterpreterTool:
    cfg = config.model_copy(update={"use_auto_container": True})
    return OpenAICodeInterpreterTool(
        config=cfg,
        container_id=None,
        company_id=company_id,
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
def test_get_tool_prompts__uses_config_system_prompt__when_uncustomised() -> None:
    """Purpose: Effective system prompt is always the stored config value (fence default)."""
    config = OpenAICodeInterpreterConfig()
    tool = _auto_container_tool(config)

    prompts = tool.get_tool_prompts()

    assert (
        prompts.tool_system_prompt == DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT_FENCE
    )
    assert "NO internet access" in prompts.tool_system_prompt


@pytest.mark.ai
def test_get_tool_prompts__uses_config_system_prompt__when_customised() -> None:
    """Purpose: Operator-customised text is returned as-is."""
    custom = "CUSTOM OPERATOR PROMPT — DO NOT REPLACE"
    config = OpenAICodeInterpreterConfig(tool_description_for_system_prompt=custom)
    tool = _auto_container_tool(config)

    prompts = tool.get_tool_prompts()

    assert prompts.tool_system_prompt == custom


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_tool__force_auto_container__sets_use_auto_container_and_returns_tool() -> (
    None
):
    """
    Purpose: Verify that force_auto_container=True mutates the config to use_auto_container=True
    and returns a tool with container_id=None, bypassing any container-creation side effects.
    Why this matters: This is the primary path for GPT-5.4 Pro which requires auto container mode
    but does not have use_auto_container set in its default config.
    """
    config = OpenAICodeInterpreterConfig(use_auto_container=False)
    tool = await OpenAICodeInterpreterTool.build_tool(
        config=config,
        uploaded_files=[],
        client=MagicMock(),
        content_service=MagicMock(),
        company_id="company-1",
        user_id="user-1",
        chat_id="chat-1",
        is_exclusive=True,
        force_auto_container=True,
    )

    assert tool._container_id is None
    assert tool.is_exclusive() is True


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_tool__use_auto_container_in_config__returns_tool_without_container() -> (
    None
):
    """
    Purpose: Verify that use_auto_container=True in the config (without force_auto_container)
    also returns a tool with container_id=None.
    Why this matters: Covers the existing config-driven auto-container path and ensures
    is_exclusive is correctly forwarded.
    """
    config = OpenAICodeInterpreterConfig(use_auto_container=True)
    tool = await OpenAICodeInterpreterTool.build_tool(
        config=config,
        uploaded_files=[],
        client=MagicMock(),
        content_service=MagicMock(),
        company_id="company-2",
        user_id="user-2",
        chat_id="chat-2",
        is_exclusive=False,
    )

    assert tool._container_id is None
    assert tool.is_exclusive() is False


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


# ============================================================================
# Tests for _upload_files_to_container (retry-wrapped download + create)
# ============================================================================


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files_to_container__downloads_and_creates__when_file_not_in_memory() -> (
    None
):
    """
    Purpose: Exercise the upload branch: download bytes from ContentService and
    ``containers.files.create`` so diff coverage includes retry-wrapped I/O.
    Why this matters: CI requires ≥60% coverage on changed lines in service.py.
    """
    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_test",
        file_ids={},
    )
    uploaded = Content(id="cont_upload_1", key="data.csv")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(
        return_value=b"a,b\n1,2\n",
    )
    openai_file = MagicMock()
    openai_file.id = "file_openai_1"
    files_create = AsyncMock(return_value=openai_file)
    client = MagicMock()
    client.containers.files.create = files_create

    result = await _upload_files_to_container(
        client=client,
        uploaded_files=[uploaded],
        memory=memory,
        content_service=content_service,
        chat_id="chat_1",
    )

    assert result.file_ids["cont_upload_1"] == "file_openai_1"
    content_service.download_content_to_bytes_async.assert_awaited_once_with(
        content_id="cont_upload_1",
        chat_id="chat_1",
    )
    files_create.assert_awaited_once()
    assert files_create.await_args.kwargs["container_id"] == "ctr_test"
    assert files_create.await_args.kwargs["file"] == ("data.csv", b"a,b\n1,2\n")


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files_to_container__retries_download__after_transient_error() -> (
    None
):
    """
    Purpose: Confirm tenacity retries ``download_content_to_bytes_async`` after a
    transient failure before calling ``containers.files.create``.
    """
    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_retry",
        file_ids={},
    )
    uploaded = Content(id="cont_retry_1", key="f.bin")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(
        side_effect=[ConnectionError("blip"), b"payload"],
    )
    openai_file = MagicMock()
    openai_file.id = "file_after_retry"
    files_create = AsyncMock(return_value=openai_file)
    client = MagicMock()
    client.containers.files.create = files_create

    result = await _upload_files_to_container(
        client=client,
        uploaded_files=[uploaded],
        memory=memory,
        content_service=content_service,
        chat_id="chat_retry",
    )

    assert result.file_ids["cont_retry_1"] == "file_after_retry"
    assert content_service.download_content_to_bytes_async.await_count == 2
    files_create.assert_awaited_once()
