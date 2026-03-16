"""Shared container and file-upload utilities for OpenAI built-in tools.

Used by both :mod:`code_interpreter` and :mod:`hosted_shell` to manage
persistent containers and file uploads via short-term memory.
"""

import logging

from openai import AsyncOpenAI, BaseModel, NotFoundError

from unique_toolkit import ContentService, ShortTermMemoryService
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.content.schemas import Content

logger = logging.getLogger(__name__)


class ContainerShortTermMemorySchema(BaseModel):
    """Short-term memory schema for persistent container state.

    Attributes:
        container_id: ID of the persistent container (``None`` when not yet
            created or when using auto containers).
        file_ids: Mapping of Unique platform content IDs to OpenAI file IDs
            so that files are only uploaded once per chat session.
    """

    container_id: str | None = None
    file_ids: dict[str, str] = {}  # Mapping of unique file id to openai file id


ContainerMemoryManager = PersistentShortMemoryManager[ContainerShortTermMemorySchema]


def get_container_memory_manager(
    company_id: str,
    user_id: str,
    chat_id: str,
    memory_name: str,
) -> ContainerMemoryManager:
    """Create a memory manager scoped to the current chat session.

    Args:
        company_id: Unique company identifier.
        user_id: Unique user identifier.
        chat_id: Unique chat identifier.
        memory_name: Key used to store/retrieve this memory entry.
    """
    short_term_memory_service = ShortTermMemoryService(
        company_id=company_id,
        user_id=user_id,
        chat_id=chat_id,
        message_id=None,
    )
    return PersistentShortMemoryManager(
        short_term_memory_service=short_term_memory_service,
        short_term_memory_schema=ContainerShortTermMemorySchema,
        short_term_memory_name=memory_name,
    )


async def create_container_if_not_exists(
    client: AsyncOpenAI,
    chat_id: str,
    user_id: str,
    company_id: str,
    expires_after_minutes: int,
    container_name_prefix: str,
    memory: ContainerShortTermMemorySchema | None = None,
    files_client: AsyncOpenAI | None = None,
) -> ContainerShortTermMemorySchema:
    """Ensure a persistent container exists, creating one if needed.

    If the container referenced in *memory* no longer exists or is inactive,
    a fresh container is created and the memory schema is reset.

    Args:
        client: An ``AsyncOpenAI`` client instance.
        chat_id: Unique chat identifier.
        user_id: Unique user identifier.
        company_id: Unique company identifier.
        expires_after_minutes: Container TTL in minutes.
        container_name_prefix: Prefix for the container name
            (e.g. ``"code_execution"`` or ``"hosted_shell"``).
        memory: Existing memory state, or ``None`` to create fresh.
    """
    if memory is not None:
        logger.info("Container found in short term memory")
    else:
        logger.info("No Container in short term memory, creating a new container")
        memory = ContainerShortTermMemorySchema()

    container_id = memory.container_id

    # Use the direct client for container operations when available (needed
    # for LiteLLM models where the proxy doesn't support /v1/containers).
    container_client = files_client or client

    if container_id is not None:
        try:
            container = await container_client.containers.retrieve(container_id)
            if container.status not in ["active", "running"]:
                logger.info(
                    "Container has status `%s`, recreating a new one", container.status
                )
                container_id = None
        except NotFoundError:
            container_id = None

    if container_id is None:
        memory = ContainerShortTermMemorySchema()

        container = await container_client.containers.create(
            name=f"{container_name_prefix}_{company_id}_{user_id}_{chat_id}",
            expires_after={
                "anchor": "last_active_at",
                "minutes": expires_after_minutes,
            },
        )

        memory.container_id = container.id

    return memory


async def upload_files_to_container(
    client: AsyncOpenAI,
    uploaded_files: list[Content],
    memory: ContainerShortTermMemorySchema,
    content_service: ContentService,
    chat_id: str,
    files_client: AsyncOpenAI | None = None,
) -> ContainerShortTermMemorySchema:
    """Upload chat files directly into a persistent container.

    Files already present (by Unique content ID) are skipped.

    Args:
        files_client: Optional direct OpenAI client for container/file
            operations, bypassing the proxy.  Falls back to *client* when
            ``None``.
    """
    # Use the direct client for container file operations when available
    # (needed for LiteLLM models where the proxy doesn't support /v1/containers).
    container_client = files_client or client

    container_id = memory.container_id

    assert container_id is not None

    memory = memory.model_copy(deep=True)

    for file in uploaded_files:
        upload = True
        if file.id in memory.file_ids:
            try:
                _ = await container_client.containers.files.retrieve(
                    container_id=container_id, file_id=memory.file_ids[file.id]
                )
                logger.info("File with id %s already uploaded to container", file.id)
                upload = False
            except NotFoundError:
                upload = True

        if upload:
            logger.info(
                "Uploading file %s to container %s", file.id, memory.container_id
            )
            file_content = await content_service.download_content_to_bytes_async(
                content_id=file.id, chat_id=chat_id
            )

            openai_file = await container_client.containers.files.create(
                container_id=container_id,
                file=(file.key, file_content),
            )
            memory.file_ids[file.id] = openai_file.id

    return memory
