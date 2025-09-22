from typing import override

from openai.types.responses.tool_param import CodeInterpreter

from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.config import (
    CodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.schemas import ToolPrompts
from unique_toolkit.content.schemas import (
    Content,
)


class OpenAICodeInterpreterTool(OpenAIBuiltInTool[CodeInterpreter]):
    def __init__(self, config: CodeInterpreterConfig, uploaded_files: list[Content]):
        self._config = config
        self._uploaded_files = uploaded_files

    @property
    @override
    def name(self) -> OpenAIBuiltInToolName:
        return OpenAIBuiltInToolName.CODE_INTERPRETER

    @override
    def tool_description(self) -> CodeInterpreter:
        return {
            "container": {
                "type": "auto",
            },
            "type": "code_interpreter",
        }

    @classmethod
    async def build_tool(
        cls, config: CodeInterpreterConfig, uploaded_files: list[Content]
    ) -> "OpenAICodeInterpreterTool":
        return cls(config, uploaded_files)

    @override
    def get_tool_prompts(self) -> ToolPrompts:
        return ToolPrompts(
            name=self.name,
            display_name="the python tool",  # https://platform.openai.com/docs/guides/tools-code-interpreter
            tool_description="Always use this tool to run code.",
            tool_system_prompt="Always use this tool to run code.",
            tool_format_information_for_system_prompt="Always use this tool to run code.",
            tool_user_prompt="Always use this tool to run code.",
            tool_format_information_for_user_prompt="Always use this tool to run code.",
            input_model={},
        )
