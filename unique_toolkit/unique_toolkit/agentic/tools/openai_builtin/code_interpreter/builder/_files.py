import asyncio
import logging

from openai import AsyncOpenAI
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    stop_after_attempt,
    wait_exponential,
)

from unique_toolkit import ContentService
from unique_toolkit._common.execution import (
    SafeTaskExecutor,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder._memory import (
    _CodeExecutionShortTermMemorySchema,
)
from unique_toolkit.content.schemas import (
    Content,
)

logger = logging.getLogger(__name__)

_UPLOAD_MAX_RETRIES = 2
_UPLOAD_RETRY_BASE_DELAY = 0.5


def _build_upload_retry() -> AsyncRetrying:
    """Exponential-backoff retry policy for transient upload/download failures.

    Matches the pattern used in the ``DisplayCodeInterpreterFilesPostProcessor``
    so that every outbound I/O call gets the same behaviour: up to
    ``_UPLOAD_MAX_RETRIES`` extra attempts, doubling the wait each time,
    with a WARNING log before each sleep.
    """
    return AsyncRetrying(
        stop=stop_after_attempt(1 + _UPLOAD_MAX_RETRIES),
        wait=wait_exponential(multiplier=_UPLOAD_RETRY_BASE_DELAY),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def _check_file_already_uploaded(
    content_id: str,
    memory: _CodeExecutionShortTermMemorySchema,
) -> bool:
    if content_id not in memory.file_paths:
        logger.info("File with id %s not in short term memory", content_id)
        return False

    return True


async def _upload_file_to_container(
    client: AsyncOpenAI,
    content_id: str,
    filename: str,
    content_service: ContentService,
    container_id: str,
) -> str:
    logger.info(
        "Uploading file %s (%s) to container %s",
        content_id,
        filename,
        container_id,
    )

    file_content = await _build_upload_retry()(
        content_service.download_content_to_bytes_async,
        content_id=content_id,
    )
    logger.info(
        "Downloaded %d bytes for file %s; uploading to container %s",
        len(file_content),
        content_id,
        container_id,
    )

    openai_file = await _build_upload_retry()(
        client.containers.files.create,
        container_id=container_id,
        file=(filename, file_content),
    )
    logger.info(
        "File %s successfully uploaded as OpenAI file %s in container %s",
        content_id,
        openai_file.id,
        container_id,
    )

    return openai_file.path


async def _upload_files_to_container(
    client: AsyncOpenAI,
    uploaded_files: list[Content],
    memory: _CodeExecutionShortTermMemorySchema,
    content_service: ContentService,
) -> tuple[_CodeExecutionShortTermMemorySchema, bool]:
    async def _check_and_upload(content: Content) -> str | None:
        if _check_file_already_uploaded(content_id=content.id, memory=memory):
            return None

        return await _upload_file_to_container(
            client=client,
            content_id=content.id,
            filename=content.key,
            content_service=content_service,
            container_id=memory.container_id,
        )

    # Deduplicate
    unique_contents = {content.id: content for content in uploaded_files}.values()

    executor = SafeTaskExecutor(logger=logger)

    results = await asyncio.gather(
        *(
            executor.execute_async(_check_and_upload, content)
            for content in unique_contents
        ),
    )

    updated = False
    for content, result in zip(unique_contents, results):
        if result.success and (filepath := result.unpack()) is not None:
            memory.file_paths[content.id] = filepath
            updated = True

    return memory, updated


async def _resolve_kb_contents(
    content_service: ContentService,
    content_ids: list[str],
) -> list[Content]:
    contents = await content_service.search_contents_async(
        where={"id": {"in": content_ids}},
    )

    found_ids = {c.id for c in contents}
    missing = [content_id for content_id in content_ids if content_id not in found_ids]
    if missing:
        logger.warning(
            "additional_uploaded_documents: %d content ids not found or not accessible in KB: %s",
            len(missing),
            missing,
        )

    return contents
