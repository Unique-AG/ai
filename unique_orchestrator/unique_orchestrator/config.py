from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema
from unique_deep_research.config import DeepResearchToolConfig
from unique_deep_research.service import DeepResearchTool
from unique_follow_up_questions.config import FollowUpQuestionsConfig
from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.service import InternalSearchTool
from unique_stock_ticker.config import StockTickerConfig
from unique_swot import SwotAnalysisTool, SwotAnalysisToolConfig
from unique_toolkit._common.validators import (
    LMI,
    ClipInt,
    get_LMI_default_field,
)
from unique_toolkit.agentic.evaluation.hallucination.constants import (
    HallucinationConfig,
)
from unique_toolkit.agentic.history_manager.history_manager import (
    UploadedContentConfig,
)
from unique_toolkit.agentic.loop_runner import (
    QWEN_FORCED_TOOL_CALL_INSTRUCTION,
    QWEN_LAST_ITERATION_INSTRUCTION,
    PlanningConfig,
)
from unique_toolkit.agentic.responses_api import (
    DisplayCodeInterpreterFilesPostProcessorConfig,
    ShowExecutedCodePostprocessorConfig,
)
from unique_toolkit.agentic.tools.a2a import (
    REFERENCING_INSTRUCTIONS_FOR_SYSTEM_PROMPT,
    REFERENCING_INSTRUCTIONS_FOR_USER_PROMPT,
)
from unique_toolkit.agentic.tools.a2a.evaluation import SubAgentEvaluationServiceConfig
from unique_toolkit.agentic.tools.openai_builtin.manager import (
    OpenAICodeInterpreterConfig,
)
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.tool import ToolBuildConfig
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ToolProgressReporterConfig,
)
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_web_search.config import WebSearchConfig
from unique_web_search.service import WebSearchTool

DeactivatedNone = Annotated[
    None,
    Field(title="Deactivated", description="None"),
]


class SpaceType(StrEnum):
    UNIQUE_CUSTOM = "unique_custom"
    UNIQUE_AI = "unique_ai"
    UNIQUE_TRANSLATION = "unique_translation"
    UNIQUE_MAGIC_TABLE = ""


T = TypeVar("T", bound=SpaceType)


class SpaceConfigBase(BaseToolConfig, Generic[T]):
    """Base class for space configuration."""

    type: T = Field(description="The type of the space.")

    project_name: str = Field(
        default="Unique AI",
        description="The project name as optained from spaces 2.0",
    )

    language_model: LMI = get_LMI_default_field(DEFAULT_GPT_4o)

    custom_instructions: str = Field(
        default="",
        description="A custom instruction provided by the system admin.",
    )

    tools: list[ToolBuildConfig] = Field(
        default=[
            ToolBuildConfig(
                name=InternalSearchTool.name,
                configuration=InternalSearchConfig(
                    exclude_uploaded_files=True,
                ),
            ),
            ToolBuildConfig(
                name=WebSearchTool.name,
                configuration=WebSearchConfig(),
            ),
            ToolBuildConfig(
                name=DeepResearchTool.name,
                configuration=DeepResearchToolConfig(),
            ),
            ToolBuildConfig(
                name=SwotAnalysisTool.name,
                configuration=SwotAnalysisToolConfig(),
            ),
        ],
    )

    @field_validator("tools", mode="after")
    @classmethod
    def set_input_context_size(
        cls, tools: list[ToolBuildConfig], info: ValidationInfo
    ) -> list[ToolBuildConfig]:
        for tool in tools:
            if tool.name == InternalSearchTool.name:
                tool.configuration.language_model_max_input_tokens = (  # type: ignore
                    info.data["language_model"].token_limits.token_limit_input
                )
            elif tool.name == WebSearchTool.name:
                tool.configuration.language_model_max_input_tokens = (  # type: ignore
                    info.data["language_model"].token_limits.token_limit_input
                )
        return tools


class UniqueAISpaceConfig(SpaceConfigBase):
    """Contains configuration for the entities that a space provides."""

    type: Literal[SpaceType.UNIQUE_AI] = SpaceType.UNIQUE_AI


UniqueAISpaceConfig.model_rebuild()

LIMIT_MAX_TOOL_CALLS_PER_ITERATION = 50


class QwenConfig(BaseToolConfig):
    """Qwen specific configuration."""

    forced_tool_call_instruction: str = Field(
        default=QWEN_FORCED_TOOL_CALL_INSTRUCTION,
        description="This instruction is appended to the user message for every forced tool call.",
    )

    last_iteration_instruction: str = Field(
        default=QWEN_LAST_ITERATION_INSTRUCTION,
        description="An assistant message with this instruction is generated once the maximum number of loop iterations is reached.",
    )


class ModelSpecificConfig(BaseToolConfig):
    """Model-specific loop configurations."""

    qwen: QwenConfig = QwenConfig()


class LoopConfiguration(BaseToolConfig):
    max_tool_calls_per_iteration: Annotated[
        int,
        *ClipInt(min_value=1, max_value=LIMIT_MAX_TOOL_CALLS_PER_ITERATION),
    ] = 10

    planning_config: (
        Annotated[PlanningConfig, Field(title="Active")] | DeactivatedNone
    ) = Field(default=None, description="Planning configuration.")

    model_specific: ModelSpecificConfig = ModelSpecificConfig()


class EvaluationConfig(BaseToolConfig):
    hallucination_config: HallucinationConfig = HallucinationConfig()


# ------------------------------------------------------------
# Space 2.0 Config
# ------------------------------------------------------------


class UniqueAIPromptConfig(BaseToolConfig):
    system_prompt_template: str = Field(
        default_factory=lambda: (
            Path(__file__).parent / "prompts" / "system_prompt.jinja2"
        ).read_text(),
        description="The system prompt template as a Jinja2 template string.",
    )

    user_message_prompt_template: str = Field(
        default_factory=lambda: (
            Path(__file__).parent / "prompts" / "user_message_prompt.jinja2"
        ).read_text(),
        description="The user message prompt template as a Jinja2 template string.",
    )

    user_metadata: list[str] = Field(
        default=[],
        title="User Metadata",
        description="User metadata fields to be ingested in the system prompt.",
    )


class UniqueAIServices(BaseToolConfig):
    """Determine the services the agent is using

    All services are optional and can be disabled by setting them to None.
    """

    follow_up_questions_config: FollowUpQuestionsConfig = FollowUpQuestionsConfig()

    stock_ticker_config: StockTickerConfig = StockTickerConfig()

    evaluation_config: EvaluationConfig = EvaluationConfig(
        hallucination_config=HallucinationConfig(),
    )

    uploaded_content_config: SkipJsonSchema[UploadedContentConfig] = (
        UploadedContentConfig()
    )

    tool_progress_reporter_config: SkipJsonSchema[ToolProgressReporterConfig] = (
        ToolProgressReporterConfig()
    )

    @field_validator("stock_ticker_config", mode="before")
    @classmethod
    def check_if_stock_ticker_config_is_none(cls, stock_ticker_config):
        """Check if the stock ticker config is none and return a default config. Required for backward compatibility."""
        if not stock_ticker_config:
            return StockTickerConfig(
                enabled=False,
            )
        return stock_ticker_config

    @field_validator("follow_up_questions_config", mode="before")
    @classmethod
    def check_if_follow_up_questions_config_is_one(cls, follow_up_questions_config):
        """Check if the follow up questions config is none and return a default config. Required for backward compatibility."""
        if not follow_up_questions_config:
            return FollowUpQuestionsConfig(
                number_of_questions=0,
            )
        return follow_up_questions_config

    @field_validator("evaluation_config", mode="before")
    @classmethod
    def check_if_evaluation_config_is_none(cls, evaluation_config):
        """Check if the evaluation config is none and return a default config. Required for backward compatibility."""
        if not evaluation_config:
            return EvaluationConfig()
        return evaluation_config


class InputTokenDistributionConfig(BaseToolConfig):
    percent_for_history: float = Field(
        default=0.2,
        ge=0.0,
        lt=1.0,
        description="The fraction of the max input tokens that will be reserved for the history.",
    )

    def max_history_tokens(self, max_input_token: int) -> int:
        return int(self.percent_for_history * max_input_token)


class SubAgentsReferencingConfig(BaseToolConfig):
    referencing_instructions_for_system_prompt: str = Field(
        default=REFERENCING_INSTRUCTIONS_FOR_SYSTEM_PROMPT,
        description="Referencing instructions for the main agent's system prompt.",
    )
    referencing_instructions_for_user_prompt: str = Field(
        default=REFERENCING_INSTRUCTIONS_FOR_USER_PROMPT,
        description="Referencing instructions for the main agent's user prompt. Should correspond to a short reminder.",
    )


class SubAgentsConfig(BaseToolConfig):
    referencing_config: (
        Annotated[SubAgentsReferencingConfig, Field(title="Active")] | DeactivatedNone
    ) = SubAgentsReferencingConfig()
    evaluation_config: (
        Annotated[SubAgentEvaluationServiceConfig, Field(title="Active")]
        | DeactivatedNone
    ) = SubAgentEvaluationServiceConfig()

    sleep_time_before_update: float = Field(
        default=0.5,
        description="Time to sleep before updating the main agent message to display the sub agent responses. Temporary fix to avoid rendering issues.",
    )


class CodeInterpreterExtendedConfig(BaseToolConfig):
    generated_files_config: DisplayCodeInterpreterFilesPostProcessorConfig = Field(
        default=DisplayCodeInterpreterFilesPostProcessorConfig(),
        title="Generated files config",
        description="Display config for generated files",
    )

    executed_code_display_config: (
        Annotated[
            ShowExecutedCodePostprocessorConfig,
            Field(title="Active"),
        ]
        | DeactivatedNone
    ) = Field(
        ShowExecutedCodePostprocessorConfig(),
        description="If active, generated code will be prepended to the LLM answer",
    )

    tool_config: OpenAICodeInterpreterConfig = Field(
        default=OpenAICodeInterpreterConfig(),
        title="Tool config",
    )


class ResponsesApiConfig(BaseToolConfig):
    code_interpreter: (
        Annotated[CodeInterpreterExtendedConfig, Field(title="Active")]
        | DeactivatedNone
    ) = Field(
        default=None,
        description="If active, the main agent will have acces to the OpenAI Code Interpreter tool",
    )

    use_responses_api: bool = Field(
        default=False,
        description="If set, the main agent will use the Responses API from OpenAI",
    )


class ExperimentalConfig(BaseToolConfig):
    """Experimental features this part of the configuration might evolve in the future continuously"""

    thinking_steps_display: SkipJsonSchema[bool] = False

    # TODO: The temperature should be used via the additional_llm_options
    # then the additional_llm_options migth should eventually be closer to the LangaugeModelInfo
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=10.0,
        description="The temperature to use for the LLM.",
    )

    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the LLM.",
    )

    loop_configuration: LoopConfiguration = LoopConfiguration(
        max_tool_calls_per_iteration=10
    )

    sub_agents_config: SubAgentsConfig = SubAgentsConfig()

    responses_api_config: ResponsesApiConfig = ResponsesApiConfig()


class UniqueAIAgentConfig(BaseToolConfig):
    max_loop_iterations: int = 8

    input_token_distribution: InputTokenDistributionConfig = Field(
        default=InputTokenDistributionConfig(),
        description="The distribution of the input tokens.",
    )

    prompt_config: UniqueAIPromptConfig = UniqueAIPromptConfig()

    services: UniqueAIServices = UniqueAIServices()

    experimental: ExperimentalConfig = ExperimentalConfig()


class UniqueAIConfig(BaseToolConfig):
    space: UniqueAISpaceConfig = UniqueAISpaceConfig()

    agent: UniqueAIAgentConfig = UniqueAIAgentConfig()

    @model_validator(mode="after")
    def disable_sub_agent_referencing_if_not_used(self) -> "UniqueAIConfig":
        if not any(tool.is_sub_agent for tool in self.space.tools):
            self.agent.experimental.sub_agents_config.referencing_config = None
        return self
