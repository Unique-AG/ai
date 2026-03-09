import logging
from typing import override

from openai import AsyncOpenAI
from openai.types.responses.tool_param import CodeInterpreter

from unique_toolkit import ContentService
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.container_utils import (
    create_container_if_not_exists,
    get_container_memory_manager,
    upload_files_to_container,
)
from unique_toolkit.agentic.tools.schemas import ToolPrompts
from unique_toolkit.content.schemas import (
    Content,
)

logger = logging.getLogger(__name__)

_MEMORY_NAME = "container_code_execution"
_CONTAINER_NAME_PREFIX = "code_execution"


class OpenAICodeInterpreterTool(OpenAIBuiltInTool[CodeInterpreter]):
    DISPLAY_NAME = "Code Interpreter"

    def __init__(
        self,
        config: OpenAICodeInterpreterConfig,
        container_id: str | None,
        is_exclusive: bool = False,
    ) -> None:
        self._config = config

        if not config.use_auto_container and container_id is None:
            raise ValueError("`container_id` required when not using `auto` containers")

        self._container_id = container_id
        self._is_exclusive = is_exclusive

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
    ) -> "OpenAICodeInterpreterTool":
        if config.use_auto_container:
            logger.info("Using `auto` container setting")
            return cls(config=config, container_id=None)

        memory_manager = get_container_memory_manager(
            company_id=company_id,
            user_id=user_id,
            chat_id=chat_id,
            memory_name=_MEMORY_NAME,
        )

        memory = await memory_manager.load_async()

        memory = await create_container_if_not_exists(
            client=client,
            memory=memory,
            chat_id=chat_id,
            user_id=user_id,
            company_id=company_id,
            expires_after_minutes=config.expires_after_minutes,
            container_name_prefix=_CONTAINER_NAME_PREFIX,
        )

        if config.upload_files_in_chat_to_container:
            memory = await upload_files_to_container(
                client=client,
                uploaded_files=uploaded_files,
                content_service=content_service,
                chat_id=chat_id,
                memory=memory,
            )

        await memory_manager.save_async(memory)

        assert memory.container_id is not None

        return OpenAICodeInterpreterTool(
            config=config, container_id=memory.container_id, is_exclusive=is_exclusive
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
