import asyncio
import logging
from typing import override

from pydantic import BaseModel, Field

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.activator.config import (
    CodeInterpreterActivatorConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.builder import (
    CodeInterpreterBuilder,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.tool import (
    OpenAICodeInterpreterTool,
)
from unique_toolkit.agentic.tools.schemas import (
    ToolCallResponse,
)
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

logger = logging.getLogger(__name__)


class _CodeParams(BaseModel):
    arg: bool = Field(True, description="Ignored Argument.")


class CodeInterpreterActivatorTool(Tool[CodeInterpreterActivatorConfig]):
    NAME = "ActivatePython"
    DISPLAY_NAME = "Activate Python"

    name = NAME

    def __init__(
        self,
        config: CodeInterpreterActivatorConfig,
        builder: CodeInterpreterBuilder,
    ) -> None:
        super().__init__(config=config)
        self._builder = builder
        self._built_tool: OpenAICodeInterpreterTool | None = None
        self._activation_lock = asyncio.Lock()

    @property
    def is_activated(self) -> bool:
        return self._built_tool is not None

    def get_activated_tool(self) -> OpenAICodeInterpreterTool:
        if self._built_tool is None:
            raise RuntimeError(
                "Code interpreter tool is not activated yet; call `run` first."
            )
        return self._built_tool

    @override
    def display_name(self) -> str:
        return self.DISPLAY_NAME

    @override
    def is_enabled(self) -> bool:
        return True

    @override
    def is_exclusive(self) -> bool:
        return False

    @override
    def is_capability(self) -> bool:
        return True

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=_CodeParams,
        )

    @override
    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    @override
    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    @override
    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        return []

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        async with self._activation_lock:
            if self._built_tool is None:
                logger.info("Building code interpreter tool")
                self._built_tool = await self._builder.build()

        return ToolCallResponse(
            id=tool_call.id,
            name=self.name,
            content="The python tool is now active. You may execute python code.",
        )
