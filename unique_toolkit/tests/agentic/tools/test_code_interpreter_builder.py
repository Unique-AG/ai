"""Tests for CodeInterpreterBuilder and the builder package helpers.

Provisioning logic (container reuse/creation, file uploads, short-term-memory
persistence, KB content resolution) was extracted from the tool class into
``code_interpreter/builder``; these tests were ported from
``test_code_interpreter_service.py`` accordingly.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder import (
    CodeInterpreterBuilder,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder._container import (
    check_container_exists,
    create_container,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder._files import (
    check_file_already_uploaded,
    resolve_kb_contents,
    upload_file_to_container,
    upload_files_to_container,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder._memory import (
    CodeExecutionShortTermMemorySchema,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.service import (
    OpenAICodeInterpreterTool,
)
from unique_toolkit.content.schemas import Content


async def _build_via_builder(**kwargs) -> OpenAICodeInterpreterTool:
    """Call CodeInterpreterBuilder with build_tool's historical signature."""
    return await CodeInterpreterBuilder(**kwargs).build()


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
    tool = await _build_via_builder(
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
    tool = await _build_via_builder(
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


# ============================================================================
# Tests for upload_files_to_container (retry-wrapped download + create)
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
        file_paths={},
    )
    uploaded = Content(id="cont_upload_1", key="data.csv")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(
        return_value=b"a,b\n1,2\n",
    )
    openai_file = MagicMock()
    openai_file.path = "/mnt/data/data.csv"
    files_create = AsyncMock(return_value=openai_file)
    client = MagicMock()
    client.containers.files.create = files_create

    result, updated = await upload_files_to_container(
        client=client,
        uploaded_files=[uploaded],
        memory=memory,
        content_service=content_service,
    )

    assert updated is True
    assert result.file_paths["cont_upload_1"] == "/mnt/data/data.csv"
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
        file_paths={},
    )
    uploaded = Content(id="cont_retry_1", key="f.bin")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(
        side_effect=[ConnectionError("blip"), b"payload"],
    )
    openai_file = MagicMock()
    openai_file.path = "/mnt/data/f.bin"
    files_create = AsyncMock(return_value=openai_file)
    client = MagicMock()
    client.containers.files.create = files_create

    result, updated = await upload_files_to_container(
        client=client,
        uploaded_files=[uploaded],
        memory=memory,
        content_service=content_service,
    )

    assert updated is True
    assert result.file_paths["cont_retry_1"] == "/mnt/data/f.bin"
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
    Purpose: Verify that upload_files_to_container only downloads/uploads each unique
    content id once, even when the input list contains duplicates.
    Why this matters: Duplicates can arise from merging chat-uploaded files with
    additional_uploaded_documents. Re-uploading wastes bandwidth and quota.
    Setup summary: Pass a list with two entries sharing the same id; assert download
    and containers.files.create are each awaited exactly once.
    """
    memory = CodeExecutionShortTermMemorySchema(container_id="ctr_dedup", file_paths={})
    duplicate = Content(id="cont_dup", key="dup.csv")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"x")
    openai_file = MagicMock()
    openai_file.path = "/mnt/data/dup.csv"
    files_create = AsyncMock(return_value=openai_file)
    client = MagicMock()
    client.containers.files.create = files_create

    result, updated = await upload_files_to_container(
        client=client,
        uploaded_files=[duplicate, duplicate],
        memory=memory,
        content_service=content_service,
    )

    assert updated is True
    assert result.file_paths == {"cont_dup": "/mnt/data/dup.csv"}
    assert content_service.download_content_to_bytes_async.await_count == 1
    files_create.assert_awaited_once()


@pytest.mark.ai
def test_check_file_already_uploaded__returns_true__when_content_id_in_memory() -> None:
    """
    Purpose: Verify that check_file_already_uploaded returns True when memory already
    has a filepath mapping for the content id — no API call required.
    Why this matters: This is the short-circuit that avoids redundant uploads on
    repeated tool builds within a chat.
    """
    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_skip",
        file_paths={"cont_skip": "/mnt/data/existing.csv"},
    )
    result = check_file_already_uploaded(content_id="cont_skip", memory=memory)

    assert result is True


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files_to_container__skips_upload__when_filepath_already_in_memory() -> (
    None
):
    """
    Purpose: Verify that a content id already present in memory.file_paths is not
    re-downloaded or re-uploaded.
    Why this matters: file_paths is now the sole source of truth for skip detection;
    no API round-trip is needed.
    """
    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_cached",
        file_paths={"cont_cached": "/mnt/data/cached.csv"},
    )
    cached = Content(id="cont_cached", key="cached.csv")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock()
    client = MagicMock()
    client.containers.files.create = AsyncMock()

    result, updated = await upload_files_to_container(
        client=client,
        uploaded_files=[cached],
        memory=memory,
        content_service=content_service,
    )

    assert updated is False
    assert result.file_paths == {"cont_cached": "/mnt/data/cached.csv"}
    content_service.download_content_to_bytes_async.assert_not_awaited()
    client.containers.files.create.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_file_to_container__returns_new_file_id__on_successful_upload() -> (
    None
):
    """
    Purpose: Verify upload_file_to_container downloads content and creates a container
    file, returning the new openai file id.
    """
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"data")
    openai_file = MagicMock()
    openai_file.path = "/mnt/data/new.csv"
    client = MagicMock()
    client.containers.files.create = AsyncMock(return_value=openai_file)

    filepath = await upload_file_to_container(
        client=client,
        content_id="cont_new",
        filename="new.csv",
        content_service=content_service,
        container_id="ctr_upload",
    )

    assert filepath == "/mnt/data/new.csv"
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
    Purpose: Verify resolve_kb_contents delegates to ContentService.search_contents_async
    with a ``{"id": {"in": [...]}}`` filter and returns the resulting contents.
    Why this matters: This is the KB lookup for additional_uploaded_documents; a wrong
    filter shape would silently return nothing and break operator-configured templates.
    Setup summary: Stub search_contents_async to return two Contents; assert the call
    shape and the returned list.
    """
    found = [Content(id="cont_a", key="a.csv"), Content(id="cont_b", key="b.csv")]
    content_service = MagicMock()
    content_service.search_contents_async = AsyncMock(return_value=found)

    result = await resolve_kb_contents(
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
    resolve_kb_contents logs a warning naming the missing ids and returns whatever was found.
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
        logger="unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder._files",
    ):
        result = await resolve_kb_contents(
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
        container_id="ctr_built", file_paths={}
    )
    memory_manager = MagicMock()
    memory_manager.load_async = AsyncMock(return_value=None)
    memory_manager.save_async = AsyncMock()

    builder_mod = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder.builder"
    with (
        patch(
            f"{builder_mod}.get_container_code_execution_short_term_memory_manager",
            return_value=memory_manager,
        ),
        patch(
            f"{builder_mod}.check_container_exists",
            AsyncMock(return_value=False),
        ),
        patch(
            f"{builder_mod}.create_container",
            AsyncMock(return_value="ctr_built"),
        ),
        patch(
            f"{builder_mod}.upload_files_to_container",
            AsyncMock(return_value=(memory_after_create, True)),
        ) as mock_upload,
    ):
        tool = await _build_via_builder(
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
    Setup summary: Pass no chat files and no KB document ids; assert upload_files_to_container
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
        container_id="ctr_empty", file_paths={}
    )
    memory_manager = MagicMock()
    memory_manager.load_async = AsyncMock(return_value=None)
    memory_manager.save_async = AsyncMock()

    builder_mod = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder.builder"
    with (
        patch(
            f"{builder_mod}.get_container_code_execution_short_term_memory_manager",
            return_value=memory_manager,
        ),
        patch(
            f"{builder_mod}.check_container_exists",
            AsyncMock(return_value=False),
        ),
        patch(
            f"{builder_mod}.create_container",
            AsyncMock(return_value="ctr_empty"),
        ),
        patch(
            f"{builder_mod}.upload_files_to_container",
            AsyncMock(return_value=(memory_after_create, True)),
        ) as mock_upload,
    ):
        tool = await _build_via_builder(
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


# ============================================================================
# Tests for check_container_exists (status + NotFoundError handling)
# ============================================================================


@pytest.mark.ai
@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["active", "running"])
async def test_check_container_exists__returns_true__when_status_is_live(
    status: str,
) -> None:
    """
    Purpose: Verify check_container_exists returns True for the two live container
    statuses (``active`` and ``running``).
    Why this matters: These are the only statuses where the cached container id can
    be reused; anything else must trigger a recreate.
    """
    memory = CodeExecutionShortTermMemorySchema(container_id="ctr_live")
    container = MagicMock()
    container.status = status
    client = MagicMock()
    client.containers.retrieve = AsyncMock(return_value=container)

    result = await check_container_exists(client=client, memory=memory)

    assert result is True
    client.containers.retrieve.assert_awaited_once_with("ctr_live")


@pytest.mark.ai
@pytest.mark.asyncio
async def test_check_container_exists__returns_false__when_not_found() -> None:
    """
    Purpose: Verify check_container_exists returns False when the container id in
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

    result = await check_container_exists(client=client, memory=memory)

    assert result is False


@pytest.mark.ai
@pytest.mark.asyncio
async def test_check_container_exists__returns_false__when_status_is_not_live() -> None:
    """
    Purpose: Verify that a container in a non-live status (e.g. ``expired``) is treated
    as missing so the caller recreates it.
    """
    memory = CodeExecutionShortTermMemorySchema(container_id="ctr_expired")
    container = MagicMock()
    container.status = "expired"
    client = MagicMock()
    client.containers.retrieve = AsyncMock(return_value=container)

    result = await check_container_exists(client=client, memory=memory)

    assert result is False


# ============================================================================
# Tests for create_container (name format + expires_after payload)
# ============================================================================


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_container__uses_scoped_name_and_expires_after() -> None:
    """
    Purpose: Verify create_container calls ``containers.create`` with the scoped name
    ``code_execution_{company}_{user}_{chat}`` and an ``expires_after`` payload anchored
    at ``last_active_at`` with the configured minutes, and returns the new container id.
    Why this matters: The scoped name is what isolates containers per chat; wrong
    wiring would leak data across chats or users.
    """
    container = MagicMock()
    container.id = "ctr_created"
    client = MagicMock()
    client.containers.create = AsyncMock(return_value=container)

    result = await create_container(
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
# Tests for failure isolation in upload_files_to_container
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
    Assert only the good one lands in memory.file_paths and ``updated`` is True.
    """
    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_isolate", file_paths={}
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
    openai_file.path = "/mnt/data/good.csv"
    client = MagicMock()
    client.containers.files.create = AsyncMock(return_value=openai_file)

    result, updated = await upload_files_to_container(
        client=client,
        uploaded_files=[bad, good],
        memory=memory,
        content_service=content_service,
    )

    assert updated is True
    assert result.file_paths == {"cont_good": "/mnt/data/good.csv"}
    assert "cont_bad" not in result.file_paths


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files_to_container__returns_updated_false__when_all_files_already_present() -> (
    None
):
    """
    Purpose: Verify that when every file is already uploaded (retrieve succeeds for
    every content id), ``upload_files_to_container`` returns ``updated=False`` and
    does not re-download or re-create anything.
    Why this matters: This is the signal that short-term memory does not need to be
    persisted — the caller relies on it to skip ``save_async``.
    """
    memory = CodeExecutionShortTermMemorySchema(
        container_id="ctr_allcached",
        file_paths={"cont_a": "/mnt/data/a.csv", "cont_b": "/mnt/data/b.csv"},
    )
    a = Content(id="cont_a", key="a.csv")
    b = Content(id="cont_b", key="b.csv")
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock()
    client = MagicMock()
    client.containers.files.create = AsyncMock()

    result, updated = await upload_files_to_container(
        client=client,
        uploaded_files=[a, b],
        memory=memory,
        content_service=content_service,
    )

    assert updated is False
    assert result.file_paths == {
        "cont_a": "/mnt/data/a.csv",
        "cont_b": "/mnt/data/b.csv",
    }
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
        container_id="ctr_existing", file_paths={"cont_cached": "/mnt/data/c.csv"}
    )
    memory_manager = MagicMock()
    memory_manager.load_async = AsyncMock(return_value=memory_loaded)
    memory_manager.save_async = AsyncMock()

    builder_mod = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder.builder"
    with (
        patch(
            f"{builder_mod}.get_container_code_execution_short_term_memory_manager",
            return_value=memory_manager,
        ),
        patch(
            f"{builder_mod}.check_container_exists",
            AsyncMock(return_value=True),
        ),
        patch(
            f"{builder_mod}.create_container",
            AsyncMock(),
        ) as mock_create,
        patch(
            f"{builder_mod}.upload_files_to_container",
            AsyncMock(return_value=(memory_loaded, False)),
        ),
    ):
        tool = await _build_via_builder(
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
        container_id="ctr_live", file_paths={}
    )
    memory_after_upload = CodeExecutionShortTermMemorySchema(
        container_id="ctr_live", file_paths={"cont_new": "/mnt/data/n.csv"}
    )
    memory_manager = MagicMock()
    memory_manager.load_async = AsyncMock(return_value=memory_loaded)
    memory_manager.save_async = AsyncMock()

    builder_mod = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder.builder"
    with (
        patch(
            f"{builder_mod}.get_container_code_execution_short_term_memory_manager",
            return_value=memory_manager,
        ),
        patch(
            f"{builder_mod}.check_container_exists",
            AsyncMock(return_value=True),
        ),
        patch(
            f"{builder_mod}.upload_files_to_container",
            AsyncMock(return_value=(memory_after_upload, True)),
        ),
    ):
        await _build_via_builder(
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
    openai_file.path = "/mnt/data/shared.csv"
    client = MagicMock()
    client.containers.files.create = AsyncMock(return_value=openai_file)

    memory_loaded = CodeExecutionShortTermMemorySchema(
        container_id="ctr_dedup_e2e", file_paths={}
    )
    memory_manager = MagicMock()
    memory_manager.load_async = AsyncMock(return_value=memory_loaded)
    memory_manager.save_async = AsyncMock()

    builder_mod = "unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder.builder"
    with (
        patch(
            f"{builder_mod}.get_container_code_execution_short_term_memory_manager",
            return_value=memory_manager,
        ),
        patch(
            f"{builder_mod}.check_container_exists",
            AsyncMock(return_value=True),
        ),
    ):
        await _build_via_builder(
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
