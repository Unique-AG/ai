from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import NotFoundError

from unique_toolkit.agentic.tools.openai_builtin.container_utils import (
    ContainerShortTermMemorySchema,
    create_container_if_not_exists,
    get_container_memory_manager,
    upload_files_to_container,
)


# ---------------------------------------------------------------------------
# ContainerShortTermMemorySchema
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_container_schema__defaults__when_no_args() -> None:
    """
    Purpose: Verify schema initialises with sensible defaults.
    Why this matters: Both code_interpreter and hosted_shell rely on these defaults.
    Setup summary: Instantiate with no args, assert fields.
    """
    schema = ContainerShortTermMemorySchema()
    assert schema.container_id is None
    assert schema.file_ids == {}


# ---------------------------------------------------------------------------
# get_container_memory_manager
# ---------------------------------------------------------------------------


@pytest.mark.ai
def test_get_container_memory_manager__returns_manager__with_given_memory_name() -> None:
    """
    Purpose: Verify factory creates a memory manager using the provided memory name.
    Why this matters: Ensures each tool gets its own isolated memory namespace.
    Setup summary: Patch ShortTermMemoryService and PersistentShortMemoryManager, assert name is forwarded.
    """
    with (
        patch(
            "unique_toolkit.agentic.tools.openai_builtin.container_utils.ShortTermMemoryService"
        ) as mock_service_cls,
        patch(
            "unique_toolkit.agentic.tools.openai_builtin.container_utils.PersistentShortMemoryManager"
        ) as mock_manager_cls,
    ):
        mock_service_cls.return_value = MagicMock()
        sentinel = MagicMock()
        mock_manager_cls.return_value = sentinel

        result = get_container_memory_manager(
            company_id="c1",
            user_id="u1",
            chat_id="ch1",
            memory_name="my_custom_name",
        )

        assert result is sentinel
        mock_manager_cls.assert_called_once()
        call_kwargs = mock_manager_cls.call_args.kwargs
        assert call_kwargs["short_term_memory_name"] == "my_custom_name"
        assert call_kwargs["short_term_memory_schema"] is ContainerShortTermMemorySchema


# ---------------------------------------------------------------------------
# create_container_if_not_exists
# ---------------------------------------------------------------------------


def _make_client(
    container_status: str = "active",
    retrieve_raises: bool = False,
) -> AsyncMock:
    """Helper to build a mock AsyncOpenAI client."""
    client = AsyncMock()
    if retrieve_raises:
        client.containers.retrieve = AsyncMock(
            side_effect=NotFoundError(
                message="not found",
                response=MagicMock(status_code=404),
                body=None,
            )
        )
    else:
        client.containers.retrieve = AsyncMock(
            return_value=SimpleNamespace(status=container_status, id="existing-id")
        )
    client.containers.create = AsyncMock(
        return_value=SimpleNamespace(id="new-container-id")
    )
    return client


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_container__creates_new__when_memory_is_none() -> None:
    """
    Purpose: Verify a new container is created when no prior memory exists.
    Why this matters: First turn of a new chat must initialise a container.
    Setup summary: Pass memory=None, assert containers.create was called.
    """
    client = _make_client()

    result = await create_container_if_not_exists(
        client=client,
        chat_id="ch1",
        user_id="u1",
        company_id="c1",
        expires_after_minutes=20,
        container_name_prefix="test_tool",
        memory=None,
    )

    assert result.container_id == "new-container-id"
    client.containers.create.assert_awaited_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_container__reuses__when_container_active() -> None:
    """
    Purpose: Verify an existing active container is reused without creating a new one.
    Why this matters: Avoids unnecessary container churn across turns.
    Setup summary: Provide memory with a container_id, mock retrieve returning active status.
    """
    client = _make_client(container_status="active")
    memory = ContainerShortTermMemorySchema(container_id="existing-id")

    result = await create_container_if_not_exists(
        client=client,
        chat_id="ch1",
        user_id="u1",
        company_id="c1",
        expires_after_minutes=20,
        container_name_prefix="test_tool",
        memory=memory,
    )

    assert result.container_id == "existing-id"
    client.containers.create.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_container__recreates__when_container_inactive() -> None:
    """
    Purpose: Verify a new container is created when the existing one is expired/stopped.
    Why this matters: Prevents using a stale container that won't accept commands.
    Setup summary: Mock retrieve returning "expired" status, assert create is called.
    """
    client = _make_client(container_status="expired")
    memory = ContainerShortTermMemorySchema(container_id="old-id")

    result = await create_container_if_not_exists(
        client=client,
        chat_id="ch1",
        user_id="u1",
        company_id="c1",
        expires_after_minutes=20,
        container_name_prefix="test_tool",
        memory=memory,
    )

    assert result.container_id == "new-container-id"
    client.containers.create.assert_awaited_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_container__recreates__when_container_not_found() -> None:
    """
    Purpose: Verify a new container is created when the existing one no longer exists.
    Why this matters: Handles the case where a container was garbage-collected.
    Setup summary: Mock retrieve raising NotFoundError, assert create is called.
    """
    client = _make_client(retrieve_raises=True)
    memory = ContainerShortTermMemorySchema(container_id="gone-id")

    result = await create_container_if_not_exists(
        client=client,
        chat_id="ch1",
        user_id="u1",
        company_id="c1",
        expires_after_minutes=20,
        container_name_prefix="test_tool",
        memory=memory,
    )

    assert result.container_id == "new-container-id"
    client.containers.create.assert_awaited_once()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_create_container__uses_correct_name_prefix() -> None:
    """
    Purpose: Verify the container name includes the provided prefix.
    Why this matters: Each tool type needs a distinct container namespace.
    Setup summary: Pass a specific prefix, inspect the containers.create call.
    """
    client = _make_client()

    await create_container_if_not_exists(
        client=client,
        chat_id="ch1",
        user_id="u1",
        company_id="c1",
        expires_after_minutes=30,
        container_name_prefix="my_prefix",
        memory=None,
    )

    call_kwargs = client.containers.create.call_args.kwargs
    assert call_kwargs["name"] == "my_prefix_c1_u1_ch1"
    assert call_kwargs["expires_after"]["minutes"] == 30


# ---------------------------------------------------------------------------
# upload_files_to_container
# ---------------------------------------------------------------------------


def _make_content(file_id: str, key: str = "file.txt") -> MagicMock:
    """Create a mock Content object."""
    content = MagicMock()
    content.id = file_id
    content.key = key
    return content


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files__skips__when_already_uploaded() -> None:
    """
    Purpose: Verify files already in the container are not re-uploaded.
    Why this matters: Avoids duplicate uploads and wasted bandwidth.
    Setup summary: Pre-populate file_ids in memory, mock retrieve returning success.
    """
    client = AsyncMock()
    client.containers.files.retrieve = AsyncMock(return_value=SimpleNamespace(id="oai-f1"))
    content_service = MagicMock()

    memory = ContainerShortTermMemorySchema(
        container_id="ctr-1",
        file_ids={"unique-f1": "oai-f1"},
    )

    result = await upload_files_to_container(
        client=client,
        uploaded_files=[_make_content("unique-f1")],
        memory=memory,
        content_service=content_service,
        chat_id="ch1",
    )

    assert result.file_ids == {"unique-f1": "oai-f1"}
    client.containers.files.create.assert_not_awaited()
    content_service.download_content_to_bytes_async.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files__uploads_new__when_not_cached() -> None:
    """
    Purpose: Verify new files are uploaded and their IDs are cached.
    Why this matters: Core file upload flow must work for both tools.
    Setup summary: Provide a file not in memory, mock create returning a new file ID.
    """
    client = AsyncMock()
    client.containers.files.create = AsyncMock(
        return_value=SimpleNamespace(id="oai-new")
    )
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"file-bytes")

    memory = ContainerShortTermMemorySchema(container_id="ctr-1")

    result = await upload_files_to_container(
        client=client,
        uploaded_files=[_make_content("unique-f2", key="data.csv")],
        memory=memory,
        content_service=content_service,
        chat_id="ch1",
    )

    assert result.file_ids == {"unique-f2": "oai-new"}
    client.containers.files.create.assert_awaited_once()
    call_kwargs = client.containers.files.create.call_args.kwargs
    assert call_kwargs["container_id"] == "ctr-1"
    assert call_kwargs["file"] == ("data.csv", b"file-bytes")


@pytest.mark.ai
@pytest.mark.asyncio
async def test_upload_files__reuploads__when_container_file_not_found() -> None:
    """
    Purpose: Verify a file is re-uploaded when the container copy is missing.
    Why this matters: Handles container file eviction gracefully.
    Setup summary: Pre-populate file_ids, mock retrieve raising NotFoundError.
    """
    client = AsyncMock()
    client.containers.files.retrieve = AsyncMock(
        side_effect=NotFoundError(
            message="not found",
            response=MagicMock(status_code=404),
            body=None,
        )
    )
    client.containers.files.create = AsyncMock(
        return_value=SimpleNamespace(id="oai-reuploaded")
    )
    content_service = MagicMock()
    content_service.download_content_to_bytes_async = AsyncMock(return_value=b"bytes")

    memory = ContainerShortTermMemorySchema(
        container_id="ctr-1",
        file_ids={"unique-f1": "oai-old"},
    )

    result = await upload_files_to_container(
        client=client,
        uploaded_files=[_make_content("unique-f1")],
        memory=memory,
        content_service=content_service,
        chat_id="ch1",
    )

    assert result.file_ids["unique-f1"] == "oai-reuploaded"
    client.containers.files.create.assert_awaited_once()
