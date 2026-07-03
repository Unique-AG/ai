from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI
from openai.types.responses import ResponseIncludable

from unique_toolkit.agentic.tools.config import ToolBuildConfig
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder import (
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
        force_auto_container: bool = False,
    ) -> OpenAIBuiltInTool[Any]:
        if tool_config.name == OpenAIBuiltInToolName.CODE_INTERPRETER:
            assert isinstance(tool_config.configuration, CodeInterpreterExtendedConfig)
            if tool_config.configuration.tool_config.lazy:
                # Lazy activation is being redesigned on top of the builder.
                raise NotImplementedError(
                    "Lazy code interpreter is not available yet."
                )
            builder = CodeInterpreterBuilder(
                config=tool_config.configuration.tool_config,
                uploaded_files=uploaded_files,
                content_service=content_service,
                client=client,
                company_id=company_id,
                user_id=user_id,
                chat_id=chat_id,
            )
            return await builder.build(
                is_exclusive=tool_config.is_exclusive,
                force_auto_container=force_auto_container,
            )
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
        builtin_tools = []
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
                cls._validate_lazy_tool_invariants(tool)
                builtin_tools.append(tool)

        return OpenAIBuiltInToolManager(builtin_tools)

    @staticmethod
    def _validate_lazy_tool_invariants(tool: OpenAIBuiltInTool[Any]) -> None:
        """A lazy built-in (one exposing an activator) must be a non-exclusive
        capability tool: the activator has to stay available to the model
        (capability) and must never wipe the rest of the tool set (exclusive).
        """
        if tool.activator() is None:
            return
        if not tool.is_capability():
            raise ValueError(
                f"Built-in tool '{tool.name}' cannot be lazy (has an activator) "
                "without being a capability tool; is_capability() must return True."
            )
        if tool.is_exclusive():
            raise ValueError(
                f"Built-in tool '{tool.name}' cannot be both lazy (has an "
                "activator) and exclusive; disable is_exclusive or lazy."
            )

    def get_all_openai_builtin_tools(self) -> list[OpenAIBuiltInTool[Any]]:
        return self._builtin_tools.copy()

    def get_required_include_params(self) -> list[ResponseIncludable]:
        """Aggregate include params required by all active built-in tools."""
        seen: set[str] = set()
        result: list[ResponseIncludable] = []
        for tool in self._builtin_tools:
            for param in tool.get_required_include_params():
                if param not in seen:
                    seen.add(param)
                    result.append(param)
        return result
