import logging
from typing import override

from openai import AsyncOpenAI, BaseModel, NotFoundError
from openai.types.responses.tool_param import CodeInterpreter

from unique_toolkit import ContentService, ShortTermMemoryService
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    CodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.schemas import ToolPrompts
from unique_toolkit.content.schemas import (
    Content,
)

logger = logging.getLogger(__name__)


SHORT_TERM_MEMORY_NAME = "container_code_execution"


class CodeExecutionShortTermMemorySchema(BaseModel):
    container_id: str | None = None
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
        short_term_memory_name=SHORT_TERM_MEMORY_NAME,
    )
    return short_term_memory_manager


async def _create_container_if_not_exists(
    client: AsyncOpenAI,
    chat_id: str,
    user_id: str,
    company_id: str,
    expires_after_minutes: int,
    memory: CodeExecutionShortTermMemorySchema | None = None,
) -> CodeExecutionShortTermMemorySchema:
    if memory is not None:
        logger.info("Container found in short term memory")
    else:
        logger.info("No Container in short term memory, creating a new container")
        memory = CodeExecutionShortTermMemorySchema()

    container_id = memory.container_id

    if container_id is not None:
        try:
            container = await client.containers.retrieve(container_id)
            if container.status not in ["active", "running"]:
                logger.info(
                    "Container has status `%s`, recreating a new one", container.status
                )
                container_id = None
        except NotFoundError:
            container_id = None

    if container_id is None:
        memory = CodeExecutionShortTermMemorySchema()

        container = await client.containers.create(
            name=f"code_execution_{company_id}_{user_id}_{chat_id}",
            expires_after={
                "anchor": "last_active_at",
                "minutes": expires_after_minutes,
            },
        )

        memory.container_id = container.id

    return memory


async def _upload_files_to_container(
    client: AsyncOpenAI,
    uploaded_files: list[Content],
    memory: CodeExecutionShortTermMemorySchema,
    content_service: ContentService,
    chat_id: str,
) -> CodeExecutionShortTermMemorySchema:
    container_id = memory.container_id

    assert container_id is not None

    memory = memory.model_copy(deep=True)

    for file in uploaded_files:
        upload = True
        if file.id in memory.file_ids:
            try:
                _ = await client.containers.files.retrieve(
                    container_id=container_id, file_id=memory.file_ids[file.id]
                )
                logger.info("File with id %s already uploaded to container", file.id)
                upload = False
            except NotFoundError:
                upload = True

        if upload:
            logger.info(
                "Uploding file %s to container %s", file.id, memory.container_id
            )
            file_content = content_service.download_content_to_bytes(
                content_id=file.id, chat_id=chat_id
            ) # TODO: Use async version when available

            openai_file = await client.containers.files.create(
                container_id=container_id,
                file=(file.key, file_content),
            )
            memory.file_ids[file.id] = openai_file.id

    return memory


class OpenAICodeInterpreterTool(OpenAIBuiltInTool[CodeInterpreter]):
    DISPLAY_NAME = "Code Interpreter"

    def __init__(
        self,
        config: CodeInterpreterConfig,
        container_id: str | None,
    ):
        self._config = config

        if not config.use_auto_container and container_id is None:
            raise ValueError("`container_id` required when not using `auto` containers")

        self._container_id = container_id

    @property
    @override
    def name(self) -> OpenAIBuiltInToolName:
        return OpenAIBuiltInToolName.CODE_INTERPRETER

    @override
    def tool_description(self) -> CodeInterpreter:
        if self._config.use_auto_container:
            return {"container": {"type": "auto"}, "type": "code_interpreter"}

        return {
            "container": self._container_id,  # type: ignore
            "type": "code_interpreter",
        }

    @classmethod
    async def build_tool(
        cls,
        config: CodeInterpreterConfig,
        uploaded_files: list[Content],
        client: AsyncOpenAI,
        content_service: ContentService,
        company_id: str,
        user_id: str,
        chat_id: str,
    ) -> "OpenAICodeInterpreterTool":
        if config.use_auto_container:
            logger.info("Using `auto` container setting")
            return cls(config=config, container_id=None)

        memory_manager = _get_container_code_execution_short_term_memory_manager(
            company_id=company_id,
            user_id=user_id,
            chat_id=chat_id,
        )

        memory = await memory_manager.load_async()

        memory = await _create_container_if_not_exists(
            client=client,
            memory=memory,
            chat_id=chat_id,
            user_id=user_id,
            company_id=company_id,
            expires_after_minutes=config.expires_after_minutes,
        )

        memory = await _upload_files_to_container(
            client=client,
            uploaded_files=uploaded_files,
            content_service=content_service,
            chat_id=chat_id,
            memory=memory,
        )

        await memory_manager.save_async(memory)

        assert memory.container_id is not None

        return OpenAICodeInterpreterTool(
            config=config, container_id=memory.container_id
        )

    @override
    def get_tool_prompts(self) -> ToolPrompts:
        return ToolPrompts(
            name="the python tool",  # https://platform.openai.com/docs/guides/tools-code-interpreter
            display_name=self.DISPLAY_NAME,
            tool_description=self._config.tool_description,
            tool_system_prompt=self._config.tool_description_for_system_prompt,
            tool_format_information_for_system_prompt=self._config.tool_format_information_for_system_prompt,
            tool_user_prompt=self._config.tool_description_for_user_prompt,
            tool_format_information_for_user_prompt=self._config.tool_format_information_for_user_prompt,
            input_model={},
        )
