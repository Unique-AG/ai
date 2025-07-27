from typing import Callable

from unique_toolkit.unique_toolkit.tools.tool_definitions import BaseToolConfig, Tool


tool_map: dict[str, type[Tool]] = {}
tool_config_map: dict[str, Callable] = {}

   
def register_tool(
    cls,
    tool: type[Tool],
    tool_config: type[BaseToolConfig],
):
    cls.tool_map[tool.name] = tool
    cls.tool_config_map[tool.name] = tool_config

   
def build_tool(cls, tool_name: str, *args, **kwargs) -> Tool:
    tool = cls.tool_map[tool_name](*args, **kwargs)
    return tool


def build_tool_config(
    cls, tool_name: str, **kwargs
) -> BaseToolConfig:
    if tool_name not in cls.tool_config_map:
        raise ValueError(f"Tool {tool_name} not found")
    return cls.tool_config_map[tool_name](**kwargs)
