from pydantic import Field

from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig


class CodeInterpreterConfig(BaseToolConfig):
    upload_files_in_chat: bool = Field(default=True)


ToolFactory.register_tool_config(
    OpenAIBuiltInToolName.CODE_INTERPRETER, CodeInterpreterConfig
)
