from pydantic import Field

from unique_toolkit.agentic.tools.schemas import (
    BaseToolConfig,
)

_DEFAULT_TOOL_DESCRIPTION = """
Activate the code interpreter to run Python in a secure environment for
calculations, data analysis, processing uploaded files (including spreadsheets),
plotting and data visualization, and generating downloadable files. 

CRITICAL: Act as though these capabilities are already available: whenever they are useful, call this tool
silently and proceed. Never mention this tool, its activation, or its setup to the user.
""".strip()

_DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT = _DEFAULT_TOOL_DESCRIPTION


class CodeInterpreterActivatorConfig(BaseToolConfig):
    tool_description: str = Field(default=_DEFAULT_TOOL_DESCRIPTION)
    tool_description_for_system_prompt: str = (
        _DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT
    )
