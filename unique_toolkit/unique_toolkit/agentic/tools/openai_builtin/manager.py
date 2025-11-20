from openai import AsyncOpenAI

from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter import (
    OpenAICodeInterpreterConfig,
    OpenAICodeInterpreterTool,
)
from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService


class OpenAIBuiltInToolManager:
    def __init__(
        self,
        builtin_tools: list[OpenAIBuiltInTool],
    ):
        self._builtin_tools = builtin_tools

    @classmethod
    async def _build_tool(
        cls,
        uploaded_files: list[Content],
        content_service: ContentService,
        user_id: str,
        company_id: str,
        chat_id: str,
        client: AsyncOpenAI,
        tool_config: ToolBuildConfig,
    ) -> OpenAIBuiltInTool:
        if tool_config.name == OpenAIBuiltInToolName.CODE_INTERPRETER:
            assert isinstance(tool_config.configuration, OpenAICodeInterpreterConfig)
            tool = await OpenAICodeInterpreterTool.build_tool(
                config=tool_config.configuration,
                uploaded_files=uploaded_files,
                content_service=content_service,
                client=client,
                company_id=company_id,
                user_id=user_id,
                chat_id=chat_id,
                is_exclusive=tool_config.is_exclusive,
                is_history_exclusive=tool_config.is_history_exclusive,
            )
            return tool
        else:
            raise ValueError(f"Unknown built-in tool name: {tool_config.name}")

    @classmethod
    async def build_manager(
        cls,
        uploaded_files: list[Content],
        content_service: ContentService,
        user_id: str,
        company_id: str,
        chat_id: str,
        client: AsyncOpenAI,
        tool_configs: list[ToolBuildConfig],
    ) -> "OpenAIBuiltInToolManager":
        builtin_tools = []
        for tool_config in tool_configs:
            if tool_config.name in OpenAIBuiltInToolName and tool_config.is_enabled:
                builtin_tools.append(
                    await cls._build_tool(
                        uploaded_files,
                        content_service,
                        user_id,
                        company_id,
                        chat_id,
                        client,
                        tool_config,
                    )
                )

        return OpenAIBuiltInToolManager(builtin_tools)

    def get_all_openai_builtin_tools(self) -> list[OpenAIBuiltInTool]:
        return self._builtin_tools.copy()
