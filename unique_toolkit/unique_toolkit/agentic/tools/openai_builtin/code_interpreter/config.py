from typing import Annotated

from pydantic import Field, field_validator

from unique_toolkit._common.config_checker import register_config
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.activator import (
    CodeInterpreterActivatorConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessorConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessorConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.tool import (
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig


@register_config()
class CodeInterpreterExtendedConfig(BaseToolConfig):
    generated_files_config: DisplayCodeInterpreterFilesPostProcessorConfig = Field(
        default=DisplayCodeInterpreterFilesPostProcessorConfig(),
        title="Generated files",
    )

    executed_code_display_config: ShowExecutedCodePostprocessorConfig = Field(
        default=ShowExecutedCodePostprocessorConfig(),
        title="Code display",
    )

    activator_config: (
        Annotated[
            CodeInterpreterActivatorConfig,
            Field(
                title="Active",
                description="Configuration for the tool allowing the model to request code execution.",
            ),
        ]
        | Annotated[None, Field(title="Deactivated")]
    ) = Field(
        default=None,
        title="Deferred Resource Provisioning",
        description="If active, the resources for code execution are not provisioned eagerly but only when the model indicates that it needs the tool.",
    )

    @field_validator("executed_code_display_config", mode="before")
    @classmethod
    def _default_executed_code_display_config(cls, v):
        if v is None:
            return ShowExecutedCodePostprocessorConfig()
        return v

    tool_config: OpenAICodeInterpreterConfig = Field(
        default=OpenAICodeInterpreterConfig(),
        title="Tool",
    )


ToolFactory.register_tool_config(
    OpenAIBuiltInToolName.CODE_INTERPRETER, CodeInterpreterExtendedConfig
)
