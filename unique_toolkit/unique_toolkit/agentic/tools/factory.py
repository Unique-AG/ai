from typing import TYPE_CHECKING, Callable

from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.tool import Tool

if TYPE_CHECKING:
    from unique_toolkit.agentic.tools.config import ToolBuildConfig


class ToolFactory:
    tool_map: dict[str, type[Tool]] = {}
    tool_config_map: dict[str, Callable] = {}

    @classmethod
    def register_tool_config(cls, tool_name: str, tool_config: type[BaseToolConfig]):
        cls.tool_config_map[tool_name] = tool_config

    @classmethod
    def register_tool(
        cls,
        tool: type[Tool],
        tool_config: type[BaseToolConfig],
    ):
        cls.tool_map[tool.name] = tool
        cls.tool_config_map[tool.name] = tool_config

    @classmethod
    def build_tool(cls, tool_name: str, *args, **kwargs) -> Tool[BaseToolConfig]:
        tool = cls.tool_map[tool_name](*args, **kwargs)
        return tool

    @classmethod
    def build_tool_with_settings(
        cls, tool_name: str, settings: "ToolBuildConfig", *args, **kwargs
    ) -> Tool[BaseToolConfig]:
        tool = cls.tool_map[tool_name](*args, **kwargs)
        tool.settings = settings
        return tool

    @classmethod
    def build_tool_config(cls, tool_name: str, **kwargs) -> BaseToolConfig:
        if tool_name not in cls.tool_config_map:
            raise ValueError(f"Tool {tool_name} not found")
        return cls.tool_config_map[tool_name](**kwargs)
