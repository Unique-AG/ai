from __future__ import annotations

from typing import Any, override

from openai.types.responses import ResponseCodeInterpreterToolCall, ResponseIncludable
from openai.types.responses.tool_param import CodeInterpreter

from unique_toolkit._common.utils.jinja.render import render_template
from unique_toolkit.agentic.feature_flags.feature_flags import feature_flags
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.tool.config import (
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.schemas import ToolPrompts


class OpenAICodeInterpreterTool(OpenAIBuiltInTool[CodeInterpreter]):
    DISPLAY_NAME = "Code Interpreter"

    def __init__(
        self,
        config: OpenAICodeInterpreterConfig,
        container_id: str | None,
        company_id: str = "",
        is_exclusive: bool = False,
        user_uploaded_files: list[str] | None = None,
        kb_uploaded_files: list[str] | None = None,
        code_execution_files: list[str] | None = None,
    ) -> None:
        self._config = config

        if not config.use_auto_container and container_id is None:
            raise ValueError("`container_id` required when not using `auto` containers")

        self._container_id = container_id
        self._company_id = company_id
        self._is_exclusive = is_exclusive

        self._user_uploaded_files = user_uploaded_files
        self._kb_uploaded_files = kb_uploaded_files
        self._code_interpreter_artifacts = code_execution_files

    @property
    @override
    def name(self) -> OpenAIBuiltInToolName:
        return OpenAIBuiltInToolName.CODE_INTERPRETER

    @override
    def tool_description(self) -> CodeInterpreter:
        if self._config.use_auto_container:
            return {"container": {"type": "auto"}, "type": "code_interpreter"}

        if self._container_id is None:
            raise ValueError("container_id must be set when not using auto containers")

        return {
            "container": self._container_id,
            "type": "code_interpreter",
        }

    @override
    def is_enabled(self) -> bool:
        return True

    @override
    def takes_control(self) -> bool:
        return False

    @override
    def is_exclusive(self) -> bool:
        return self._is_exclusive

    @override
    def is_capability(self) -> bool:
        return True

    @override
    def get_tool_prompts(self) -> ToolPrompts:
        rendered_prompt = render_template(
            self._config.tool_description_for_system_prompt,
            user_uploaded_files=self._user_uploaded_files,
            kb_uploaded_files=self._kb_uploaded_files,
            code_interpreter_artifacts=self._code_interpreter_artifacts,
        )
        return ToolPrompts(
            name="python",  # https://platform.openai.com/docs/guides/tools-code-interpreter
            display_name=self.DISPLAY_NAME,
            tool_description=self._config.tool_description,
            tool_system_prompt=rendered_prompt,
            tool_format_information_for_system_prompt="",
            tool_user_prompt=self._config.tool_description_for_user_prompt,
            tool_format_information_for_user_prompt="",
            input_model={},
        )

    @override
    def display_name(self) -> str:
        return self.DISPLAY_NAME

    @override
    def get_required_include_params(self) -> list[ResponseIncludable]:
        if feature_flags.enable_code_execution_fence_un_17972.is_enabled(
            self._company_id
        ):
            return ["code_interpreter_call.outputs"]
        return []

    @classmethod
    def get_debug_info(cls, call: ResponseCodeInterpreterToolCall) -> dict[str, Any]:
        return {
            "id": call.id,
            "container_id": call.container_id,
            "code": call.code,
        }
