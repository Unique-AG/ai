import asyncio
import logging
import time

from openai import AsyncOpenAI

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder._memory import (
    CodeExecutionShortTermMemorySchema,
)

logger = logging.getLogger(__name__)

# Statuses in which a container accepts file uploads and code execution.
LIVE_CONTAINER_STATUSES = frozenset({"active", "running"})

# Best-effort wait for a live status before the first upload; on deadline we
# proceed anyway and rely on the upload retry.
CONTAINER_READY_TIMEOUT_SECONDS = 10.0
CONTAINER_READY_POLL_INTERVAL_SECONDS = 0.5


def is_container_live(status: str | None) -> bool:
    return status in LIVE_CONTAINER_STATUSES


async def check_container_exists(
    client: AsyncOpenAI,
    memory: CodeExecutionShortTermMemorySchema,
) -> bool:
    try:
        container = await client.containers.retrieve(memory.container_id)
    # The error here is sometimes InternalServerError, and sometimes a NotFoundError. We catch everything and re-create on exception
    except Exception:
        logger.exception("Container %s not found", memory.container_id)
        return False

    if not is_container_live(container.status):
        logger.info(
            "Container %s has status `%s`, recreating a new one",
            memory.container_id,
            container.status,
        )
        return False

    logger.info("Container %s found in short term memory", memory.container_id)
    return True


async def wait_until_container_live(
    client: AsyncOpenAI,
    container_id: str,
    initial_status: str | None,
    *,
    timeout_seconds: float = CONTAINER_READY_TIMEOUT_SECONDS,
    poll_interval_seconds: float = CONTAINER_READY_POLL_INTERVAL_SECONDS,
) -> None:
    """Poll ``containers.retrieve`` until the container reports a live status.

    Returns immediately (no API call) when ``initial_status`` is already live.
    Never raises: on deadline or retrieve errors it logs and returns so the
    caller can still attempt the upload.
    """
    if is_container_live(initial_status):
        return

    logger.info(
        "Container %s created with status `%s`, waiting up to %.0fs for it to become live",
        container_id,
        initial_status,
        timeout_seconds,
    )
    deadline = time.monotonic() + timeout_seconds
    status = initial_status
    while time.monotonic() < deadline:
        await asyncio.sleep(poll_interval_seconds)
        try:
            container = await client.containers.retrieve(container_id)
        except Exception:
            logger.warning(
                "Failed to retrieve status of container %s while waiting for it to become live",
                container_id,
                exc_info=True,
            )
            return
        status = container.status
        if is_container_live(status):
            logger.info("Container %s is now `%s`", container_id, status)
            return
        logger.info("Container %s still has status `%s`", container_id, status)

    logger.warning(
        "Container %s did not become live within %.0fs (last status `%s`); proceeding with upload anyway",
        container_id,
        timeout_seconds,
        status,
    )


async def create_container(
    client: AsyncOpenAI,
    chat_id: str,
    user_id: str,
    company_id: str,
    expires_after_minutes: int,
) -> str:
    container = await client.containers.create(
        name=f"code_execution_{company_id}_{user_id}_{chat_id}",
        expires_after={
            "anchor": "last_active_at",
            "minutes": expires_after_minutes,
        },
    )
    logger.info(
        "Created new container %s with status `%s`", container.id, container.status
    )
    await wait_until_container_live(
        client=client,
        container_id=container.id,
        initial_status=container.status,
    )
    return container.id
