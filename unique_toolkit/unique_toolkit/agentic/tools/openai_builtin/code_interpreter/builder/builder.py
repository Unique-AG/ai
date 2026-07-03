import logging

from openai import AsyncOpenAI
from pydantic import ValidationError

from unique_toolkit import ContentService
from unique_toolkit._common.execution import (
    failsafe_async,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder._container import (
    check_container_exists,
    create_container,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder._files import (
    resolve_kb_contents,
    upload_files_to_container,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder._memory import (
    CodeExecutionShortTermMemorySchema,
    get_container_code_execution_short_term_memory_manager,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.artifacts import (
    load_code_execution_metadata,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.tool import (
    OpenAICodeInterpreterConfig,
    OpenAICodeInterpreterTool,
)
from unique_toolkit.content.schemas import (
    Content,
)

logger = logging.getLogger(__name__)


class CodeInterpreterBuilder:
    """Provisions an ``OpenAICodeInterpreterTool``.

    Owns the construction side of the code interpreter: warm-container reuse
    via short-term memory, container creation, chat/KB file uploads, and the
    final tool instantiation. The tool class itself stays a pure runtime
    representation.
    """

    def __init__(
        self,
        config: OpenAICodeInterpreterConfig,
        uploaded_files: list[Content],
        client: AsyncOpenAI,
        content_service: ContentService,
        company_id: str,
        user_id: str,
        chat_id: str,
        is_exclusive: bool = False,
        force_auto_container: bool = False,
    ) -> None:
        self._config = config
        self._uploaded_files = uploaded_files
        self._client = client
        self._content_service = content_service
        self._company_id = company_id
        self._user_id = user_id
        self._chat_id = chat_id
        self._is_exclusive = is_exclusive
        self._force_auto_container = force_auto_container

    async def build(self) -> OpenAICodeInterpreterTool:
        is_exclusive = self._is_exclusive
        force_auto_container = self._force_auto_container
        config = self._config
        uploaded_files = self._uploaded_files
        client = self._client
        content_service = self._content_service
        company_id = self._company_id
        user_id = self._user_id
        chat_id = self._chat_id

        if force_auto_container:
            config = config.model_copy(update={"use_auto_container": True})

        if config.use_auto_container:
            logger.info("Using `auto` container setting")
            return OpenAICodeInterpreterTool(
                config=config,
                container_id=None,
                company_id=company_id,
                is_exclusive=is_exclusive,
            )

        memory_manager = get_container_code_execution_short_term_memory_manager(
            company_id=company_id,
            user_id=user_id,
            chat_id=chat_id,
        )

        # Ignore old memory schema
        memory = await failsafe_async(
            failure_return_value=None, exceptions=(ValidationError,), log_exc_info=False
        )(memory_manager.load_async)()

        container_updated = False
        if memory is None or not await check_container_exists(
            client=client, memory=memory
        ):
            container_id = await create_container(
                client=client,
                chat_id=chat_id,
                user_id=user_id,
                company_id=company_id,
                expires_after_minutes=config.expires_after_minutes,
            )
            memory = CodeExecutionShortTermMemorySchema(container_id=container_id)
            container_updated = True

        code_execution_files = []
        user_uploaded_files = []
        for content in uploaded_files:
            if (metadata := load_code_execution_metadata(content)) is not None:
                code_execution_files.append(content)
                if metadata.container_id == memory.container_id:
                    # Already available in container
                    memory.file_paths[content.id] = metadata.filepath
            else:
                user_uploaded_files.append(content)

        files_to_upload: list[Content] = []

        if config.upload_files_in_chat_to_container:
            files_to_upload.extend(uploaded_files)

        kb_files = []
        if config.additional_uploaded_documents:
            kb_files = await resolve_kb_contents(
                content_service=content_service,
                content_ids=config.additional_uploaded_documents,
            )
            files_to_upload.extend(kb_files)

        files_updated = False
        if files_to_upload:
            memory, files_updated = await upload_files_to_container(
                client=client,
                uploaded_files=files_to_upload,
                content_service=content_service,
                memory=memory,
            )

        if container_updated or files_updated:
            await memory_manager.save_async(memory)

        def _extract_paths(contents: list[Content]) -> list[str]:
            return [
                memory.file_paths[content.id]
                for content in contents
                if content.id in memory.file_paths
            ]

        return OpenAICodeInterpreterTool(
            config=config,
            container_id=memory.container_id,
            company_id=company_id,
            is_exclusive=is_exclusive,
            user_uploaded_files=_extract_paths(user_uploaded_files),
            kb_uploaded_files=_extract_paths(kb_files),
            code_execution_files=_extract_paths(code_execution_files),
        )
