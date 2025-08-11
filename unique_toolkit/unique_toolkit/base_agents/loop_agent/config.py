from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator

from unique_toolkit.unique_toolkit._common.validators import LMI, ClipInt
from unique_toolkit.unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName
from unique_toolkit.unique_toolkit.tools.config import ToolBuildConfig, get_configuration_dict



class LoopAgentTokenLimitsConfig(BaseModel):
    model_config = get_configuration_dict()

    language_model: LMI = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_1120)

    percent_of_max_tokens_for_history: float = Field(
        default=0.2,
        ge=0.0,
        lt=1.0,
        description="The fraction of the max input tokens that will be reserved for the history.",
    )

    @property
    def max_history_tokens(self) -> int:
        return int(
            self.language_model.token_limits.token_limit_input
            * self.percent_of_max_tokens_for_history,
        )


LIMIT_LOOP_ITERATIONS = 50
LIMIT_MAX_TOOL_CALLS_PER_ITERATION = 50


class LoopConfiguration(BaseModel):
    model_config = get_configuration_dict()

    max_tool_calls_per_iteration: Annotated[
        int,
        *ClipInt(min_value=1, max_value=LIMIT_MAX_TOOL_CALLS_PER_ITERATION),
    ] = 10


class LoopAgentConfig(BaseModel):
    model_config = get_configuration_dict()
    ##############################
    ### Language Model Configurations
    ##############################

    # Spaces 2.0
    language_model: LMI = LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_1120)

    temperature: float = 0.0
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )

    ##############################
    ### General Configurations
    ##############################
    max_loop_iterations: Annotated[
        int, *ClipInt(min_value=1, max_value=LIMIT_LOOP_ITERATIONS)
    ] = 8

    loop_configuration: LoopConfiguration = LoopConfiguration()

    ##############################
    ### Token Limit Configurations
    ##############################
    token_limits: LoopAgentTokenLimitsConfig = Field(default=None) # type: ignore

    ##############################
    ### Tool Configurations
    ##############################
    tools: list[ToolBuildConfig] = Field(
        default=[],
        description="A list of tool build configurations.",
    )

    ##############################
    ### Thinking steps
    ##############################
    thinking_steps_display: bool = False

    @model_validator(mode="after")
    def initialize_token_limits(cls, values):
        if values.token_limits is None:
            values.token_limits = LoopAgentTokenLimitsConfig(
                language_model=values.language_model,
            )
        return values

    @property
    def available_tools(self) -> list[str]:
        """Dynamically generate available tools from tool_configs."""
        return [tool_config.name for tool_config in self.tools]

    def get_tool_config(self, tool: str) -> BaseModel:
        """Get the tool configuration by name."""
        for tool_build_config in self.tools:
            if tool_build_config.name == tool:
                return tool_build_config.configuration
        raise ValueError(f"Unknown tool {tool}")
