from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
from unique_deep_research.config import DeepResearchToolConfig
from unique_deep_research.service import DeepResearchTool
from unique_follow_up_questions.config import FollowUpQuestionsConfig
from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.service import InternalSearchTool
from unique_stock_ticker.config import StockTickerConfig
from unique_toolkit._common.validators import (
    LMI,
    ClipInt,
    get_LMI_default_field,
)
from unique_toolkit.agentic.evaluation.hallucination.constants import (
    HallucinationConfig,
)
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.history_manager.history_manager import (
    UploadedContentConfig,
)
from unique_toolkit.agentic.tools.a2a import (
    REFERENCING_INSTRUCTIONS_FOR_SYSTEM_PROMPT,
    REFERENCING_INSTRUCTIONS_FOR_USER_PROMPT,
)
from unique_toolkit.agentic.tools.a2a.evaluation import SubAgentEvaluationServiceConfig
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.agentic.tools.tool import ToolBuildConfig
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_web_search.config import WebSearchConfig
from unique_web_search.service import WebSearchTool


class SpaceType(StrEnum):
    UNIQUE_CUSTOM = "unique_custom"
    UNIQUE_AI = "unique_ai"
    UNIQUE_TRANSLATION = "unique_translation"
    UNIQUE_MAGIC_TABLE = ""


T = TypeVar("T", bound=SpaceType)


class SpaceConfigBase(BaseModel, Generic[T]):
    """Base class for space configuration."""

    model_config = get_configuration_dict(frozen=True)
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


class LoopConfiguration(BaseModel):
    model_config = get_configuration_dict()

    max_tool_calls_per_iteration: Annotated[
        int,
        *ClipInt(min_value=1, max_value=LIMIT_MAX_TOOL_CALLS_PER_ITERATION),
    ] = 10


class EvaluationConfig(BaseModel):
    model_config = get_configuration_dict()
    max_review_steps: int = 3
    hallucination_config: HallucinationConfig = HallucinationConfig()
    sub_agents_config: SubAgentEvaluationServiceConfig | None = (
        SubAgentEvaluationServiceConfig()
    )


# ------------------------------------------------------------
# Space 2.0 Config
# ------------------------------------------------------------


class UniqueAIPromptConfig(BaseModel):
    model_config = get_configuration_dict(frozen=True)

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


DeactivatedNone = Annotated[
    None,
    Field(title="Deactivated", description="None"),
]


class UniqueAIServices(BaseModel):
    """Determine the services the agent is using

    All services are optional and can be disabled by setting them to None.
    """

    model_config = get_configuration_dict(frozen=True)

    follow_up_questions_config: (
        Annotated[
            FollowUpQuestionsConfig,
            Field(
                title="Active",
            ),
        ]
        | DeactivatedNone
    ) = FollowUpQuestionsConfig()

    stock_ticker_config: (
        Annotated[StockTickerConfig, Field(title="Active")] | DeactivatedNone
    ) = StockTickerConfig()

    evaluation_config: (
        Annotated[
            EvaluationConfig,
            Field(title="Active"),
        ]
        | DeactivatedNone
    ) = EvaluationConfig(
        hallucination_config=HallucinationConfig(),
        max_review_steps=0,
    )

    uploaded_content_config: UploadedContentConfig = UploadedContentConfig()


class InputTokenDistributionConfig(BaseModel):
    model_config = get_configuration_dict(frozen=True)

    percent_for_history: float = Field(
        default=0.2,
        ge=0.0,
        lt=1.0,
        description="The fraction of the max input tokens that will be reserved for the history.",
    )

    def max_history_tokens(self, max_input_token: int) -> int:
        return int(self.percent_for_history * max_input_token)


class SubAgentsConfig(BaseModel):
    model_config = get_configuration_dict()
    use_sub_agent_references: bool = Field(
        default=True,
        description="Whether to use sub agent references in the main agent's response. Only has an effect if sub agents are used.",
    )
    referencing_instructions_for_system_prompt: str = Field(
        default=REFERENCING_INSTRUCTIONS_FOR_SYSTEM_PROMPT,
        description="Referencing instructions for the main agent's system prompt.",
    )
    referencing_instructions_for_user_prompt: str = Field(
        default=REFERENCING_INSTRUCTIONS_FOR_USER_PROMPT,
        description="Referencing instructions for the main agent's user prompt. Should correspond to a short reminder.",
    )


class ExperimentalConfig(BaseModel):
    """Experimental features this part of the configuration might evolve in the future continuously"""

    model_config = get_configuration_dict(frozen=True)

    thinking_steps_display: bool = False

    # TODO: @gustavhartz, the Hallucination check should be triggered if enabled and the answer contains references.
    force_checks_on_stream_response_references: list[EvaluationMetricName] = Field(
        default=[EvaluationMetricName.HALLUCINATION],
        description="A list of checks to force on references. This is used to add hallucination check to references without new tool calls.",
    )

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
        max_tool_calls_per_iteration=5
    )

    sub_agents_config: SubAgentsConfig = SubAgentsConfig()


class UniqueAIAgentConfig(BaseModel):
    model_config = get_configuration_dict(frozen=True)

    max_loop_iterations: int = 8

    input_token_distribution: InputTokenDistributionConfig = Field(
        default=InputTokenDistributionConfig(),
        description="The distribution of the input tokens.",
    )

    prompt_config: UniqueAIPromptConfig = UniqueAIPromptConfig()

    services: UniqueAIServices = UniqueAIServices()

    experimental: ExperimentalConfig = ExperimentalConfig()


class UniqueAIConfig(BaseModel):
    model_config = get_configuration_dict(frozen=True)

    space: UniqueAISpaceConfig = UniqueAISpaceConfig()

    agent: UniqueAIAgentConfig = UniqueAIAgentConfig()

    @model_validator(mode="after")
    def disable_sub_agent_referencing_if_not_used(self) -> "UniqueAIConfig":
        if not any(tool.is_sub_agent for tool in self.space.tools):
            self.agent.experimental.sub_agents_config.use_sub_agent_references = False
        return self
