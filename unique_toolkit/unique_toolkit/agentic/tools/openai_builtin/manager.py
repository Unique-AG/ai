from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter import (
    CodeInterpreterActivatorTool,
    CodeInterpreterBuilder,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    CodeInterpreterExtendedConfig,
)
from unique_toolkit.content.schemas import Content
from unique_toolkit.content.service import ContentService


class OpenAIBuiltInToolManager:
    def __init__(
        self,
        builtin_tools: list[OpenAIBuiltInTool[Any]],
        activator_tools: list[CodeInterpreterActivatorTool] | None = None,
    ):
        self._builtin_tools = builtin_tools
        self._activator_tools = activator_tools or []

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
        force_auto_container: bool = False,
    ) -> OpenAIBuiltInTool[Any] | CodeInterpreterActivatorTool:
        if tool_config.name == OpenAIBuiltInToolName.CODE_INTERPRETER:
            assert isinstance(tool_config.configuration, CodeInterpreterExtendedConfig)

            activator_config = tool_config.configuration.activator_config
            if activator_config is not None and tool_config.is_exclusive:
                raise ValueError(
                    "A deferred code interpreter tool cannot be exclusive."
                )

            builder = CodeInterpreterBuilder(
                config=tool_config.configuration.tool_config,
                uploaded_files=uploaded_files,
                client=client,
                content_service=content_service,
                company_id=company_id,
                user_id=user_id,
                chat_id=chat_id,
                is_exclusive=tool_config.is_exclusive,
                force_auto_container=force_auto_container,
            )

            # Deferred: offer a cheap activator function tool now and provision
            # the container only when the model calls it.
            if activator_config is not None:
                return CodeInterpreterActivatorTool(
                    config=activator_config,
                    builder=builder,
                )

            # Eager: provision the container up front.
            return await builder.build()
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
        force_auto_container: bool = False,
    ) -> OpenAIBuiltInToolManager:
        builtin_tools: list[OpenAIBuiltInTool[Any]] = []
        activator_tools: list[CodeInterpreterActivatorTool] = []
        for tool_config in tool_configs:
            if tool_config.name in OpenAIBuiltInToolName and tool_config.is_enabled:
                tool = await cls._build_tool(
                    uploaded_files,
                    content_service,
                    user_id,
                    company_id,
                    chat_id,
                    client,
                    tool_config,
                    force_auto_container,
                )
                if isinstance(tool, CodeInterpreterActivatorTool):
                    activator_tools.append(tool)
                else:
                    builtin_tools.append(tool)

        return OpenAIBuiltInToolManager(builtin_tools, activator_tools)

    def get_all_openai_builtin_tools(self) -> list[OpenAIBuiltInTool[Any]]:
        return self._builtin_tools.copy()

    def get_activator_tools(self) -> list[CodeInterpreterActivatorTool]:
        return self._activator_tools.copy()
