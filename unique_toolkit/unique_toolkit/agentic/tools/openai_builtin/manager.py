from openai import AsyncOpenAI

from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter import (
    CodeInterpreterConfig,
    OpenAICodeInterpreterTool,
)
from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService


class OpenAIBuiltInToolManager:
    def __init__(
        self,
        uploaded_files: list[Content],
        content_service: ContentService,
        user_id: str,
        company_id: str,
        chat_id: str,
        client: AsyncOpenAI,
    ):
        self._uploaded_files = uploaded_files
        self._content_service = content_service
        self._user_id = user_id
        self._company_id = company_id
        self._client = client
        self._chat_id = chat_id

    async def _build_tool(self, tool_config: ToolBuildConfig) -> OpenAIBuiltInTool:
        if tool_config.name == OpenAIBuiltInToolName.CODE_INTERPRETER:
            assert isinstance(tool_config.configuration, CodeInterpreterConfig)
            tool = await OpenAICodeInterpreterTool.build_tool(
                config=tool_config.configuration,
                uploaded_files=self._uploaded_files,
                user_id=self._user_id,
                company_id=self._company_id,
                chat_id=self._chat_id,
                content_service=self._content_service,
                client=self._client,
            )
            return tool
        else:
            raise ValueError(f"Unknown built-in tool name: {tool_config.name}")

    async def get_all_openai_builtin_tools(
        self, tool_configs: list[ToolBuildConfig]
    ) -> tuple[list[ToolBuildConfig], list[OpenAIBuiltInTool]]:
        openai_builtin_tools = []
        filtered_tool_configs = []

        for tool_config in tool_configs:
            if tool_config.name not in OpenAIBuiltInToolName:
                filtered_tool_configs.append(tool_config)
                continue

            openai_builtin_tools.append(await self._build_tool(tool_config))

        return filtered_tool_configs, openai_builtin_tools
