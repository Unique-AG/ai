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
    _resolve_kb_contents,
    _upload_file_to_container,
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
    )

    assert result.file_ids["cont_upload_1"] == "file_openai_1"
    content_service.download_content_to_bytes_async.assert_awaited_once_with(
        content_id="cont_upload_1",
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
    )

    assert result.file_ids["cont_retry_1"] == "file_after_retry"
    assert content_service.download_content_to_bytes_async.await_count == 2
    files_create.assert_awaited_once()


# ============================================================================
# Tests for deduplication, skip-if-already-uploaded, and KB content resolution
# ============================================================================


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files_to_container__deduplicates_by_content_id__when_duplicates_present() -> (
    None
):
    """
    Purpose: Verify that _upload_files_to_container only downloads/uploads each unique
    content id once, even when the input list contains duplicates.
    Why this matters: Duplicates can arise from merging chat-uploaded files with
    additional_uploaded_documents. Re-uploading wastes bandwidth and quota.
    Setup summary: Pass a list with two entries sharing the same id; assert download
    and containers.files.create are each awaited exactly once.
    """
    memory = CodeExecutionShortTermMemorySchema(container_id="ctr_dedup", file_ids={})
    duplicate = Content(id="cont_dup", key="dup.csv")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"x")
    openai_file = MagicMock()
    openai_file.id = "file_dup"
    files_create = AsyncMock(return_value=openai_file)
    client = MagicMock()
    client.containers.files.create = files_create

    result = await _upload_files_to_container(
        client=client,
        uploaded_files=[duplicate, duplicate],
        memory=memory,
        content_service=content_service,
    )

    assert result.file_ids == {"cont_dup": "file_dup"}
    assert content_service.download_content_to_bytes_async.await_count == 1
    files_create.assert_awaited_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_file_to_container__skips_upload__when_already_present_in_container() -> (
    None
):
    """
    Purpose: Verify that _upload_file_to_container short-circuits when memory already
    maps the content id to a container file and containers.files.retrieve succeeds.
    Why this matters: Avoids redundant uploads on repeated tool builds within a chat.
    Setup summary: Pre-populate memory.file_ids; stub retrieve to return a file; assert
    no download or create is attempted.
    """
    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_skip",
        file_ids={"cont_skip": "file_existing"},
    )
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock()
    client = MagicMock()
    client.containers.files.retrieve = AsyncMock(return_value=MagicMock())
    client.containers.files.create = AsyncMock()

    await _upload_file_to_container(
        client=client,
        content_id="cont_skip",
        filename="skip.csv",
        memory=memory,
        content_service=content_service,
    )

    client.containers.files.retrieve.assert_awaited_once_with(
        container_id="ctr_skip", file_id="file_existing"
    )
    content_service.download_content_to_bytes_async.assert_not_awaited()
    client.containers.files.create.assert_not_awaited()
    assert memory.file_ids == {"cont_skip": "file_existing"}


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_file_to_container__reuploads__when_retrieve_raises_not_found() -> (
    None
):
    """
    Purpose: Verify that when the cached container file id no longer exists (NotFoundError
    from retrieve), the file is re-downloaded and re-uploaded and memory is refreshed.
    Why this matters: Container files expire; stale memory entries must not permanently
    block re-uploads.
    Setup summary: Seed memory with a stale mapping; retrieve raises NotFoundError;
    create returns a new file; assert memory is updated with the new openai file id.
    """
    from httpx import Request, Response
    from openai import NotFoundError

    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_stale",
        file_ids={"cont_stale": "file_gone"},
    )
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"bytes")
    new_file = MagicMock()
    new_file.id = "file_new"
    not_found = NotFoundError(
        message="gone",
        response=Response(404, request=Request("GET", "https://x")),
        body=None,
    )
    client = MagicMock()
    client.containers.files.retrieve = AsyncMock(side_effect=not_found)
    client.containers.files.create = AsyncMock(return_value=new_file)

    await _upload_file_to_container(
        client=client,
        content_id="cont_stale",
        filename="stale.csv",
        memory=memory,
        content_service=content_service,
    )

    content_service.download_content_to_bytes_async.assert_awaited_once_with(
        content_id="cont_stale",
    )
    client.containers.files.create.assert_awaited_once()
    assert memory.file_ids["cont_stale"] == "file_new"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_resolve_kb_contents__returns_search_results__and_queries_by_id_in() -> (
    None
):
    """
    Purpose: Verify _resolve_kb_contents delegates to ContentService.search_contents_async
    with a ``{"id": {"in": [...]}}`` filter and returns the resulting contents.
    Why this matters: This is the KB lookup for additional_uploaded_documents; a wrong
    filter shape would silently return nothing and break operator-configured templates.
    Setup summary: Stub search_contents_async to return two Contents; assert the call
    shape and the returned list.
    """
    found = [Content(id="cont_a", key="a.csv"), Content(id="cont_b", key="b.csv")]
    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=found)

    result = await _resolve_kb_contents(
        content_service=content_service,
        content_ids=["cont_a", "cont_b"],
    )

    assert result == found
    content_service.search_contents_async.assert_awaited_once_with(
        where={"id": {"in": ["cont_a", "cont_b"]}},
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_resolve_kb_contents__logs_warning_and_returns_partial__when_some_ids_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Purpose: Verify that when search_contents_async returns fewer contents than requested,
    _resolve_kb_contents logs a warning naming the missing ids and returns whatever was found.
    Why this matters: Operators need visibility when a configured template/content id is not
    accessible; silently ignoring would make misconfigurations invisible in production.
    Setup summary: Search returns only one of two requested ids; assert warning contains
    the missing id and the returned list matches the search result.
    """
    found = [Content(id="cont_present", key="p.csv")]
    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=found)

    with caplog.at_level(
        "WARNING",
        logger="unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service",
    ):
        result = await _resolve_kb_contents(
            content_service=content_service,
            content_ids=["cont_present", "cont_missing"],
        )

    assert result == found
    assert any(
        "cont_missing" in record.message
        and "additional_uploaded_documents" in record.message
        for record in caplog.records
    )


# ============================================================================
# Tests for build_tool integration with additional_uploaded_documents
# ============================================================================


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_tool__uploads_kb_documents__when_additional_uploaded_documents_set() -> (
    None
):
    """
    Purpose: End-to-end check that build_tool resolves KB content ids listed in
    ``additional_uploaded_documents`` and forwards them to the upload path, while
    also including chat-uploaded files when ``upload_files_in_chat_to_container`` is on.
    Why this matters: This is the feature's integration seam; a regression here would
    silently drop template/always-available files from operator configs.
    Setup summary: Configure both sources; patch the container-creation and upload
    helpers; assert the upload helper is called with the union of files.
    """
    config = OpenAICodeInterpreterConfig(
        use_auto_container=False,
        upload_files_in_chat_to_container=True,
        additional_uploaded_documents=["cont_kb1"],
    )
    chat_file = Content(id="cont_chat1", key="chat.csv")
    kb_file = Content(id="cont_kb1", key="template.csv")

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[kb_file])

    memory_after_create = CodeExecutionShortTermMemorySchema(
        container_id="ctr_built", file_ids={}
    )
    memory_manager = MagicMock()
    memory_manager.load_async = AsyncMock(return_value=None)
    memory_manager.save_async = AsyncMock()

    service_mod = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service"
    with (
        patch(
            f"{service_mod}._get_container_code_execution_short_term_memory_manager",
            return_value=memory_manager,
        ),
        patch(
            f"{service_mod}._create_container_if_not_exists",
            AsyncMock(return_value=memory_after_create),
        ),
        patch(
            f"{service_mod}._upload_files_to_container",
            AsyncMock(return_value=memory_after_create),
        ) as mock_upload,
    ):
        tool = await OpenAICodeInterpreterTool.build_tool(
            config=config,
            uploaded_files=[chat_file],
            client=MagicMock(),
            content_service=content_service,
            company_id="co",
            user_id="u",
            chat_id="c",
        )

    assert tool._container_id == "ctr_built"
    mock_upload.assert_awaited_once()
    passed_files = mock_upload.await_args.kwargs["uploaded_files"]
    assert [f.id for f in passed_files] == ["cont_chat1", "cont_kb1"]
    content_service.search_contents_async.assert_awaited_once_with(
        where={"id": {"in": ["cont_kb1"]}},
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_tool__skips_upload__when_no_sources_enabled() -> None:
    """
    Purpose: Verify build_tool does not invoke the upload helper when neither
    ``upload_files_in_chat_to_container`` nor ``additional_uploaded_documents`` supplies files.
    Why this matters: Avoids redundant work and KB lookups for the common empty-config case.
    Setup summary: Pass no chat files and no KB document ids; assert _upload_files_to_container
    and search_contents_async are never called.
    """
    config = OpenAICodeInterpreterConfig(
        use_auto_container=False,
        upload_files_in_chat_to_container=False,
        additional_uploaded_documents=[],
    )

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock()

    memory_after_create = CodeExecutionShortTermMemorySchema(
        container_id="ctr_empty", file_ids={}
    )
    memory_manager = MagicMock()
    memory_manager.load_async = AsyncMock(return_value=None)
    memory_manager.save_async = AsyncMock()

    service_mod = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service"
    with (
        patch(
            f"{service_mod}._get_container_code_execution_short_term_memory_manager",
            return_value=memory_manager,
        ),
        patch(
            f"{service_mod}._create_container_if_not_exists",
            AsyncMock(return_value=memory_after_create),
        ),
        patch(
            f"{service_mod}._upload_files_to_container",
            AsyncMock(return_value=memory_after_create),
        ) as mock_upload,
    ):
        tool = await OpenAICodeInterpreterTool.build_tool(
            config=config,
            uploaded_files=[],
            client=MagicMock(),
            content_service=content_service,
            company_id="co",
            user_id="u",
            chat_id="c",
        )

    assert tool._container_id == "ctr_empty"
    mock_upload.assert_not_awaited()
    content_service.search_contents_async.assert_not_awaited()


@pytest.mark.ai
def test_config__additional_uploaded_documents__defaults_to_empty_list() -> None:
    """
    Purpose: Verify that OpenAICodeInterpreterConfig.additional_uploaded_documents defaults
    to an empty list so existing configs keep their prior behaviour.
    Why this matters: This field was added as an additive change; an unexpected default
    would retroactively enable KB lookups for every deployment.
    Setup summary: Construct a config with no explicit value; assert the field is [].
    """
    config = OpenAICodeInterpreterConfig()
    assert config.additional_uploaded_documents == []
