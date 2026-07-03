import logging

from openai import AsyncOpenAI

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder._memory import (
    _CodeExecutionShortTermMemorySchema,
)

logger = logging.getLogger(__name__)


async def _check_container_exists(
    client: AsyncOpenAI,
    memory: _CodeExecutionShortTermMemorySchema,
) -> bool:
    try:
        container = await client.containers.retrieve(memory.container_id)
    # The error here is sometimes InternalServerError, and sometimes a NotFoundError. We catch everything and re-create on exception
    except Exception:
        logger.exception("Container %s not found", memory.container_id)
        return False

    if container.status not in ["active", "running"]:
        logger.info(
            "Container %s has status `%s`, recreating a new one",
            memory.container_id,
            container.status,
        )
        return False

    logger.info("Container %s found in short term memory", memory.container_id)
    return True


async def _create_container(
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
    logger.info("Created new container %s", container.id)
    return container.id
