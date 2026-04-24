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
    _check_container_exists,
    _check_file_already_uploaded,
    _create_container,
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

    result, updated = await _upload_files_to_container(
        client=client,
        uploaded_files=[uploaded],
        memory=memory,
        content_service=content_service,
    )

    assert updated is True
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

    result, updated = await _upload_files_to_container(
        client=client,
        uploaded_files=[uploaded],
        memory=memory,
        content_service=content_service,
    )

    assert updated is True
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

    result, updated = await _upload_files_to_container(
        client=client,
        uploaded_files=[duplicate, duplicate],
        memory=memory,
        content_service=content_service,
    )

    assert updated is True
    assert result.file_ids == {"cont_dup": "file_dup"}
    assert content_service.download_content_to_bytes_async.await_count == 1
    files_create.assert_awaited_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_check_file_already_uploaded__returns_true__when_retrieve_succeeds() -> (
    None
):
    """
    Purpose: Verify that _check_file_already_uploaded returns True when memory has a
    mapping for the content id and containers.files.retrieve succeeds.
    Why this matters: This is the short-circuit that avoids redundant uploads on
    repeated tool builds within a chat.
    """
    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_skip",
        file_ids={"cont_skip": "file_existing"},
    )
    client = MagicMock()
    client.containers.files.retrieve = AsyncMock(return_value=MagicMock())

    result = await _check_file_already_uploaded(
        client=client, content_id="cont_skip", memory=memory
    )

    assert result is True
    client.containers.files.retrieve.assert_awaited_once_with(
        container_id="ctr_skip", file_id="file_existing"
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files_to_container__reuploads__when_retrieve_raises_error() -> (
    None
):
    """
    Purpose: Verify that when the cached container file id no longer exists (the retrieve
    call raises), _upload_files_to_container re-downloads and re-uploads the file and
    records the new openai file id in memory.
    Why this matters: Container files expire; stale memory entries must not permanently
    block re-uploads.
    Setup summary: Seed memory with a stale mapping; retrieve raises OpenAIError; create
    returns a new file; assert memory is updated with the new openai file id.
    """
    from openai import OpenAIError

    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_stale",
        file_ids={"cont_stale": "file_gone"},
    )
    stale = Content(id="cont_stale", key="stale.csv")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"bytes")
    new_file = MagicMock()
    new_file.id = "file_new"
    client = MagicMock()
    client.containers.files.retrieve = AsyncMock(side_effect=OpenAIError("gone"))
    client.containers.files.create = AsyncMock(return_value=new_file)

    result, updated = await _upload_files_to_container(
        client=client,
        uploaded_files=[stale],
        memory=memory,
        content_service=content_service,
    )

    assert updated is True
    assert result.file_ids["cont_stale"] == "file_new"
    content_service.download_content_to_bytes_async.assert_awaited_once_with(
        content_id="cont_stale",
    )
    client.containers.files.create.assert_awaited_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_file_to_container__returns_new_file_id__on_successful_upload() -> (
    None
):
    """
    Purpose: Verify _upload_file_to_container downloads content and creates a container
    file, returning the new openai file id.
    """
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"data")
    openai_file = MagicMock()
    openai_file.id = "file_created"
    client = MagicMock()
    client.containers.files.create = AsyncMock(return_value=openai_file)

    file_id = await _upload_file_to_container(
        client=client,
        content_id="cont_new",
        filename="new.csv",
        content_service=content_service,
        container_id="ctr_upload",
    )

    assert file_id == "file_created"
    content_service.download_content_to_bytes_async.assert_awaited_once_with(
        content_id="cont_new",
    )
    client.containers.files.create.assert_awaited_once()
    assert client.containers.files.create.await_args.kwargs["container_id"] == (
        "ctr_upload"
    )


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
            f"{service_mod}._check_container_exists",
            AsyncMock(return_value=False),
        ),
        patch(
            f"{service_mod}._create_container",
            AsyncMock(return_value="ctr_built"),
        ),
        patch(
            f"{service_mod}._upload_files_to_container",
            AsyncMock(return_value=(memory_after_create, True)),
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
            f"{service_mod}._check_container_exists",
            AsyncMock(return_value=False),
        ),
        patch(
            f"{service_mod}._create_container",
            AsyncMock(return_value="ctr_empty"),
        ),
        patch(
            f"{service_mod}._upload_files_to_container",
            AsyncMock(return_value=(memory_after_create, True)),
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


# ============================================================================
# Tests for _check_container_exists (status + NotFoundError handling)
# ============================================================================


@pytest.mark.ai
@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["active", "running"])
async def test_check_container_exists__returns_true__when_status_is_live(
    status: str,
) -> None:
    """
    Purpose: Verify _check_container_exists returns True for the two live container
    statuses (``active`` and ``running``).
    Why this matters: These are the only statuses where the cached container id can
    be reused; anything else must trigger a recreate.
    """
    memory = CodeExecutionShortTermMemorySchema(container_id="ctr_live")
    container = MagicMock()
    container.status = status
    client = MagicMock()
    client.containers.retrieve = AsyncMock(return_value=container)

    result = await _check_container_exists(client=client, memory=memory)

    assert result is True
    client.containers.retrieve.assert_awaited_once_with("ctr_live")


@pytest.mark.ai
@pytest.mark.asyncio
async def test_check_container_exists__returns_false__when_not_found() -> None:
    """
    Purpose: Verify _check_container_exists returns False when the container id in
    memory no longer exists (NotFoundError from the OpenAI client).
    Why this matters: Containers expire; stale memory must not block rebuilding.
    """
    from httpx import Request, Response
    from openai import NotFoundError

    memory = CodeExecutionShortTermMemorySchema(container_id="ctr_gone")
    not_found = NotFoundError(
        message="gone",
        response=Response(404, request=Request("GET", "https://x")),
        body=None,
    )
    client = MagicMock()
    client.containers.retrieve = AsyncMock(side_effect=not_found)

    result = await _check_container_exists(client=client, memory=memory)

    assert result is False


@pytest.mark.ai
@pytest.mark.asyncio
async def test_check_container_exists__returns_false__when_status_is_not_live() -> (
    None
):
    """
    Purpose: Verify that a container in a non-live status (e.g. ``expired``) is treated
    as missing so the caller recreates it.
    """
    memory = CodeExecutionShortTermMemorySchema(container_id="ctr_expired")
    container = MagicMock()
    container.status = "expired"
    client = MagicMock()
    client.containers.retrieve = AsyncMock(return_value=container)

    result = await _check_container_exists(client=client, memory=memory)

    assert result is False


# ============================================================================
# Tests for _create_container (name format + expires_after payload)
# ============================================================================


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_container__uses_scoped_name_and_expires_after() -> None:
    """
    Purpose: Verify _create_container calls ``containers.create`` with the scoped name
    ``code_execution_{company}_{user}_{chat}`` and an ``expires_after`` payload anchored
    at ``last_active_at`` with the configured minutes, and returns the new container id.
    Why this matters: The scoped name is what isolates containers per chat; wrong
    wiring would leak data across chats or users.
    """
    container = MagicMock()
    container.id = "ctr_created"
    client = MagicMock()
    client.containers.create = AsyncMock(return_value=container)

    result = await _create_container(
        client=client,
        chat_id="chat-1",
        user_id="user-1",
        company_id="company-1",
        expires_after_minutes=15,
    )

    assert result == "ctr_created"
    client.containers.create.assert_awaited_once_with(
        name="code_execution_company-1_user-1_chat-1",
        expires_after={"anchor": "last_active_at", "minutes": 15},
    )


# ============================================================================
# Tests for failure isolation in _upload_files_to_container
# ============================================================================


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files_to_container__isolates_failures__one_file_fails_others_succeed() -> (
    None
):
    """
    Purpose: Verify that when one file's upload raises, sibling uploads still complete
    and the successful ids are recorded in memory.
    Why this matters: This is the reason ``SafeTaskExecutor`` replaced a bare
    ``asyncio.gather``; without isolation one bad file would cancel every other upload
    in the batch.
    Setup summary: Two files; downloader raises for ``bad``, returns bytes for ``good``.
    Assert only the good one lands in memory.file_ids and ``updated`` is True.
    """
    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_isolate", file_ids={}
    )
    good = Content(id="cont_good", key="good.csv")
    bad = Content(id="cont_bad", key="bad.csv")

    async def download(*, content_id: str) -> bytes:
        if content_id == "cont_bad":
            raise RuntimeError("download boom")
        return b"good bytes"

    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(side_effect=download)
    openai_file = MagicMock()
    openai_file.id = "file_good"
    client = MagicMock()
    client.containers.files.create = AsyncMock(return_value=openai_file)

    result, updated = await _upload_files_to_container(
        client=client,
        uploaded_files=[bad, good],
        memory=memory,
        content_service=content_service,
    )

    assert updated is True
    assert result.file_ids == {"cont_good": "file_good"}
    assert "cont_bad" not in result.file_ids


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files_to_container__returns_updated_false__when_all_files_already_present() -> (
    None
):
    """
    Purpose: Verify that when every file is already uploaded (retrieve succeeds for
    every content id), ``_upload_files_to_container`` returns ``updated=False`` and
    does not re-download or re-create anything.
    Why this matters: This is the signal that short-term memory does not need to be
    persisted — the caller relies on it to skip ``save_async``.
    """
    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_allcached",
        file_ids={"cont_a": "file_a", "cont_b": "file_b"},
    )
    a = Content(id="cont_a", key="a.csv")
    b = Content(id="cont_b", key="b.csv")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock()
    client = MagicMock()
    client.containers.files.retrieve = AsyncMock(return_value=MagicMock())
    client.containers.files.create = AsyncMock()

    result, updated = await _upload_files_to_container(
        client=client,
        uploaded_files=[a, b],
        memory=memory,
        content_service=content_service,
    )

    assert updated is False
    assert result.file_ids == {"cont_a": "file_a", "cont_b": "file_b"}
    content_service.download_content_to_bytes_async.assert_not_awaited()
    client.containers.files.create.assert_not_awaited()


# ============================================================================
# Tests for build_tool conditional save_async gating
# ============================================================================


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_tool__skips_save_async__when_container_and_files_unchanged() -> (
    None
):
    """
    Purpose: Verify that when the existing container is still live and the upload
    helper reports no changes, ``build_tool`` does not persist short-term memory.
    Why this matters: This is the optimisation motivating the ``(memory, updated)``
    tuple — unnecessary STM writes on every tool build would be wasteful.
    """
    config = OpenAICodeInterpreterConfig(
        use_auto_container=False,
        upload_files_in_chat_to_container=True,
        additional_uploaded_documents=[],
    )
    chat_file = Content(id="cont_cached", key="c.csv")

    memory_loaded = CodeExecutionShortTermMemorySchema(
        container_id="ctr_existing", file_ids={"cont_cached": "file_cached"}
    )
    memory_manager = MagicMock()
    memory_manager.load_async = AsyncMock(return_value=memory_loaded)
    memory_manager.save_async = AsyncMock()

    service_mod = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service"
    with (
        patch(
            f"{service_mod}._get_container_code_execution_short_term_memory_manager",
            return_value=memory_manager,
        ),
        patch(
            f"{service_mod}._check_container_exists",
            AsyncMock(return_value=True),
        ),
        patch(
            f"{service_mod}._create_container",
            AsyncMock(),
        ) as mock_create,
        patch(
            f"{service_mod}._upload_files_to_container",
            AsyncMock(return_value=(memory_loaded, False)),
        ),
    ):
        tool = await OpenAICodeInterpreterTool.build_tool(
            config=config,
            uploaded_files=[chat_file],
            client=MagicMock(),
            content_service=MagicMock(),
            company_id="co",
            user_id="u",
            chat_id="c",
        )

    assert tool._container_id == "ctr_existing"
    memory_manager.save_async.assert_not_awaited()
    mock_create.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_tool__saves_when_files_updated__even_if_container_unchanged() -> (
    None
):
    """
    Purpose: Verify that when the container is live but a new file was uploaded,
    ``build_tool`` still persists short-term memory.
    Why this matters: The files flag must drive persistence independently of the
    container flag.
    """
    config = OpenAICodeInterpreterConfig(
        use_auto_container=False,
        upload_files_in_chat_to_container=True,
        additional_uploaded_documents=[],
    )
    chat_file = Content(id="cont_new", key="n.csv")

    memory_loaded = CodeExecutionShortTermMemorySchema(
        container_id="ctr_live", file_ids={}
    )
    memory_after_upload = CodeExecutionShortTermMemorySchema(
        container_id="ctr_live", file_ids={"cont_new": "file_new"}
    )
    memory_manager = MagicMock()
    memory_manager.load_async = AsyncMock(return_value=memory_loaded)
    memory_manager.save_async = AsyncMock()

    service_mod = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service"
    with (
        patch(
            f"{service_mod}._get_container_code_execution_short_term_memory_manager",
            return_value=memory_manager,
        ),
        patch(
            f"{service_mod}._check_container_exists",
            AsyncMock(return_value=True),
        ),
        patch(
            f"{service_mod}._upload_files_to_container",
            AsyncMock(return_value=(memory_after_upload, True)),
        ),
    ):
        await OpenAICodeInterpreterTool.build_tool(
            config=config,
            uploaded_files=[chat_file],
            client=MagicMock(),
            content_service=MagicMock(),
            company_id="co",
            user_id="u",
            chat_id="c",
        )

    memory_manager.save_async.assert_awaited_once_with(memory_after_upload)


# ============================================================================
# Test for end-to-end dedup across chat files and KB files
# ============================================================================


@pytest.mark.ai
@pytest.mark.asyncio
async def test_build_tool__deduplicates_chat_and_kb_overlap__uploads_each_content_once() -> (
    None
):
    """
    Purpose: Verify that when the same content id is passed both as a chat-uploaded
    file and as part of ``additional_uploaded_documents``, it is downloaded and
    uploaded only once.
    Why this matters: Operators can configure a template that a user also happens to
    attach in the chat; we must not pay for the same bytes twice.
    Setup summary: Same id appears in both lists; real upload helper runs against
    mocked client + content service; assert exactly one download/create.
    """
    config = OpenAICodeInterpreterConfig(
        use_auto_container=False,
        upload_files_in_chat_to_container=True,
        additional_uploaded_documents=["cont_overlap"],
    )
    shared = Content(id="cont_overlap", key="shared.csv")

    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=[shared])
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"x")

    openai_file = MagicMock()
    openai_file.id = "file_shared"
    client = MagicMock()
    client.containers.files.create = AsyncMock(return_value=openai_file)

    memory_loaded = CodeExecutionShortTermMemorySchema(
        container_id="ctr_dedup_e2e", file_ids={}
    )
    memory_manager = MagicMock()
    memory_manager.load_async = AsyncMock(return_value=memory_loaded)
    memory_manager.save_async = AsyncMock()

    service_mod = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service"
    with (
        patch(
            f"{service_mod}._get_container_code_execution_short_term_memory_manager",
            return_value=memory_manager,
        ),
        patch(
            f"{service_mod}._check_container_exists",
            AsyncMock(return_value=True),
        ),
    ):
        await OpenAICodeInterpreterTool.build_tool(
            config=config,
            uploaded_files=[shared],
            client=client,
            content_service=content_service,
            company_id="co",
            user_id="u",
            chat_id="c",
        )

    assert content_service.download_content_to_bytes_async.await_count == 1
    assert client.containers.files.create.await_count == 1
