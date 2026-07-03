from pydantic import Field

from unique_toolkit.agentic.tools.schemas import (
    BaseToolConfig,
)

_DEFAULT_TOOL_DESCRIPTION = """
Use this tool in order to activate the code interpreter tool in this environment, which allows you to execute python code in a secure environment.
""".strip()

_DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = _DEFAULT_TOOL_DESCRIPTION


class CodeInterpreterActivatorConfig(BaseToolConfig):
    tool_description: str = Field(default=_DEFAULT_TOOL_DESCRIPTION)
    tool_description_for_system_prompt: str = (
        _DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT
    )
