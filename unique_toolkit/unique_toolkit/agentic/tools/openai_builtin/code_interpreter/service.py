from __future__ import annotations

import asyncio
import logging
from typing import Any, override

from openai import (
    AsyncOpenAI,
    BaseModel,
    NotFoundError,
    OpenAIError,
)
from openai.types.responses import ResponseCodeInterpreterToolCall, ResponseIncludable
from openai.types.responses.tool_param import CodeInterpreter
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    stop_after_attempt,
    wait_exponential,
)

from unique_toolkit import ContentService, ShortTermMemoryService
from unique_toolkit._common.execution import SafeTaskExecutor
from unique_toolkit.agentic.feature_flags.feature_flags import feature_flags
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.schemas import ToolPrompts
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


_SHORT_TERM_MEMORY_NAME = "container_code_execution"


class CodeExecutionShortTermMemorySchema(BaseModel):
    container_id: str
    file_ids: dict[str, str] = {}  # Mapping of unique file id to openai file id


CodeExecutionMemoryManager = PersistentShortMemoryManager[
    CodeExecutionShortTermMemorySchema
]


def _get_container_code_execution_short_term_memory_manager(
    company_id: str, user_id: str, chat_id: str
) -> CodeExecutionMemoryManager:
    short_term_memory_service = ShortTermMemoryService(
        company_id=company_id,
        user_id=user_id,
        chat_id=chat_id,
        message_id=None,
    )
    short_term_memory_manager = PersistentShortMemoryManager(
        short_term_memory_service=short_term_memory_service,
        short_term_memory_schema=CodeExecutionShortTermMemorySchema,
        short_term_memory_name=_SHORT_TERM_MEMORY_NAME,
    )
    return short_term_memory_manager


async def _check_container_exists(
    client: AsyncOpenAI,
    memory: CodeExecutionShortTermMemorySchema,
) -> bool:
    try:
        container = await client.containers.retrieve(memory.container_id)
    except NotFoundError:
        logger.info("Container %s not found", memory.container_id)
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


async def _check_file_already_uploaded(
    client: AsyncOpenAI,
    content_id: str,
    memory: CodeExecutionShortTermMemorySchema,
) -> bool:
    container_id = memory.container_id

    if content_id not in memory.file_ids:
        logger.info("File with id %s not in short term memory", content_id)
        return False

    file_id = memory.file_ids[content_id]
    try:
        await client.containers.files.retrieve(
            container_id=container_id, file_id=file_id
        )
        logger.info("File with id %s already uploaded to container", content_id)
        return True
    except OpenAIError:  # Azure API Errors are not stable
        logger.exception("Error while retrieving file %s", file_id)
        return False


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

    return openai_file.id


async def _upload_files_to_container(
    client: AsyncOpenAI,
    uploaded_files: list[Content],
    memory: CodeExecutionShortTermMemorySchema,
    content_service: ContentService,
) -> tuple[CodeExecutionShortTermMemorySchema, bool]:

    async def _check_and_upload(content: Content) -> str | None:
        if await _check_file_already_uploaded(
            client=client, content_id=content.id, memory=memory
        ):
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
        if result.success and (file_id := result.unpack()) is not None:
            memory.file_ids[content.id] = file_id
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


class OpenAICodeInterpreterTool(OpenAIBuiltInTool[CodeInterpreter]):
    DISPLAY_NAME = "Code Interpreter"

    def __init__(
        self,
        config: OpenAICodeInterpreterConfig,
        container_id: str | None,
        company_id: str = "",
        is_exclusive: bool = False,
    ) -> None:
        self._config = config

        if not config.use_auto_container and container_id is None:
            raise ValueError("`container_id` required when not using `auto` containers")

        self._container_id = container_id
        self._company_id = company_id
        self._is_exclusive = is_exclusive

    @property
    @override
    def name(self) -> OpenAIBuiltInToolName:
        return OpenAIBuiltInToolName.CODE_INTERPRETER

    @override
    def tool_description(self) -> CodeInterpreter:
        if self._config.use_auto_container:
            return {"container": {"type": "auto"}, "type": "code_interpreter"}

        if self._container_id is None:
            raise ValueError("container_id must be set when not using auto containers")

        return {
            "container": self._container_id,
            "type": "code_interpreter",
        }

    @override
    def is_enabled(self) -> bool:
        return True

    @override
    def takes_control(self) -> bool:
        return False

    @override
    def is_exclusive(self) -> bool:
        return self._is_exclusive

    @classmethod
    async def build_tool(
        cls,
        config: OpenAICodeInterpreterConfig,
        uploaded_files: list[Content],
        client: AsyncOpenAI,
        content_service: ContentService,
        company_id: str,
        user_id: str,
        chat_id: str,
        is_exclusive: bool = False,
        force_auto_container: bool = False,
    ) -> OpenAICodeInterpreterTool:
        if force_auto_container:
            config = config.model_copy(update={"use_auto_container": True})

        if config.use_auto_container:
            logger.info("Using `auto` container setting")
            return cls(
                config=config,
                container_id=None,
                company_id=company_id,
                is_exclusive=is_exclusive,
            )

        memory_manager = _get_container_code_execution_short_term_memory_manager(
            company_id=company_id,
            user_id=user_id,
            chat_id=chat_id,
        )

        memory = await memory_manager.load_async()

        container_updated = False
        if memory is None or not await _check_container_exists(
            client=client, memory=memory
        ):
            container_id = await _create_container(
                client=client,
                chat_id=chat_id,
                user_id=user_id,
                company_id=company_id,
                expires_after_minutes=config.expires_after_minutes,
            )
            memory = CodeExecutionShortTermMemorySchema(container_id=container_id)
            container_updated = True

        files_to_upload: list[Content] = []
        if config.upload_files_in_chat_to_container:
            files_to_upload.extend(uploaded_files)

        if config.additional_uploaded_documents:
            files_to_upload.extend(
                await _resolve_kb_contents(
                    content_service=content_service,
                    content_ids=config.additional_uploaded_documents,
                )
            )

        files_updated = False
        if files_to_upload:
            memory, files_updated = await _upload_files_to_container(
                client=client,
                uploaded_files=files_to_upload,
                content_service=content_service,
                memory=memory,
            )

        if container_updated or files_updated:
            await memory_manager.save_async(memory)

        return OpenAICodeInterpreterTool(
            config=config,
            container_id=memory.container_id,
            company_id=company_id,
            is_exclusive=is_exclusive,
        )

    @override
    def get_tool_prompts(self) -> ToolPrompts:
        return ToolPrompts(
            name="python",  # https://platform.openai.com/docs/guides/tools-code-interpreter
            display_name=self.DISPLAY_NAME,
            tool_description=self._config.tool_description,
            tool_system_prompt=self._config.tool_description_for_system_prompt,
            tool_format_information_for_system_prompt="",
            tool_user_prompt=self._config.tool_description_for_user_prompt,
            tool_format_information_for_user_prompt="",
            input_model={},
        )

    @override
    def display_name(self) -> str:
        return self.DISPLAY_NAME

    @override
    def get_required_include_params(self) -> list[ResponseIncludable]:
        if feature_flags.enable_code_execution_fence_un_17972.is_enabled(
            self._company_id
        ):
            return ["code_interpreter_call.outputs"]
        return []

    @classmethod
    def get_debug_info(cls, call: ResponseCodeInterpreterToolCall) -> dict[str, Any]:
        return {
            "id": call.id,
            "container_id": call.container_id,
            "code": call.code,
        }
