from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, ValidationInfo, field_validator
from unique_deep_research.config import DeepResearchToolConfig
from unique_deep_research.service import DeepResearchTool
from unique_follow_up_questions.config import FollowUpQuestionsConfig
from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.service import InternalSearchTool
from unique_stock_ticker.config import StockTickerConfig
from unique_toolkit._common.default_language_model import DEFAULT_GPT_4o
from unique_toolkit._common.validators import (
    LMI,
    ClipInt,
    get_LMI_default_field,
)
from unique_toolkit.evals.hallucination.constants import HallucinationConfig
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.history_manager.history_manager import (
    UploadedContentConfig,
)
from unique_toolkit.language_model import LanguageModelName
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
)
from unique_toolkit.tools.config import get_configuration_dict
from unique_toolkit.tools.factory import ToolFactory
from unique_toolkit.tools.schemas import BaseToolConfig
from unique_toolkit.tools.tool import ToolBuildConfig
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

LIMIT_LOOP_ITERATIONS = 50
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


class LoopAgentTokenLimitsConfig(BaseModel):
    model_config = get_configuration_dict()

    language_model: LMI = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_1120
    )

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


class SearchAgentConfig(BaseModel):
    """Configure the search agent."""

    model_config = get_configuration_dict(frozen=True)

    language_model: LMI = LanguageModelInfo.from_name(DEFAULT_GPT_4o)

    token_limits: LoopAgentTokenLimitsConfig = Field(
        default=LoopAgentTokenLimitsConfig(
            percent_of_max_tokens_for_history=0.6
        )
    )
    temperature: float = 0.0
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )

    # Space 2.0
    project_name: str = Field(
        default="Unique AI",
        description="The project name as optained from spaces 2.0",
    )

    # Space 2.0
    custom_instructions: str = Field(
        default="",
        description="A custom instruction provided by the system admin.",
    )

    thinking_steps_display: bool = False

    ##############################
    ### General Configurations
    ##############################
    max_loop_iterations: Annotated[
        int, *ClipInt(min_value=1, max_value=LIMIT_LOOP_ITERATIONS)
    ] = 8

    loop_configuration: LoopConfiguration = LoopConfiguration()

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

    ##############################
    ### Follow-up Questions
    ##############################
    follow_up_questions_config: FollowUpQuestionsConfig = (
        FollowUpQuestionsConfig()
    )

    ##############################
    ### Evaluation
    ##############################
    evaluation_config: EvaluationConfig = EvaluationConfig(
        hallucination_config=HallucinationConfig(),
        max_review_steps=0,
    )

    ##############################
    ### Stock Ticker
    ##############################
    stock_ticker_config: StockTickerConfig = StockTickerConfig()

    # TODO: generalize this there should only be 1 point in the code where we do the tool check.
    def get_tool_config(self, tool: str) -> BaseToolConfig:
        """Get the tool configuration by name."""
        return ToolFactory.build_tool_config(tool)

    # TODO: @gustavhartz, the Hallucination check should be triggered if enabled and the answer contains references.
    force_checks_on_stream_response_references: list[EvaluationMetricName] = (
        Field(
            default=[EvaluationMetricName.HALLUCINATION],
            description="A list of checks to force on references. This is used to add hallucination check to references without new tool calls.",
        )
    )

    uploaded_content_config: UploadedContentConfig = Field(
        default_factory=UploadedContentConfig,
        description="The uploaded content config.",
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


class ExperimentalConfig(BaseModel):
    """Experimental features this part of the configuration might evolve in the future continuously"""

    model_config = get_configuration_dict(frozen=True)

    thinking_steps_display: bool = False

    # TODO: @gustavhartz, the Hallucination check should be triggered if enabled and the answer contains references.
    force_checks_on_stream_response_references: list[EvaluationMetricName] = (
        Field(
            default=[EvaluationMetricName.HALLUCINATION],
            description="A list of checks to force on references. This is used to add hallucination check to references without new tool calls.",
        )
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


# ---
# Configuration adapter SearchAgentConfig -> UniqueAISpaceConfig
# --


def search_agent_config_to_unique_ai_space_config(
    search_agent_config: SearchAgentConfig,
) -> UniqueAIConfig:
    space = UniqueAISpaceConfig(
        project_name=search_agent_config.project_name,
        custom_instructions=search_agent_config.custom_instructions,
        tools=search_agent_config.tools,
        language_model=search_agent_config.language_model,
        type=SpaceType.UNIQUE_AI,
    )

    prompt_config = UniqueAIPromptConfig(
        system_prompt_template=search_agent_config.system_prompt_template,
        user_message_prompt_template=search_agent_config.user_message_prompt_template,
    )

    services = UniqueAIServices(
        follow_up_questions_config=search_agent_config.follow_up_questions_config,
        evaluation_config=search_agent_config.evaluation_config,
        stock_ticker_config=search_agent_config.stock_ticker_config,
        uploaded_content_config=search_agent_config.uploaded_content_config,
    )

    experimental = ExperimentalConfig(
        thinking_steps_display=search_agent_config.thinking_steps_display,
        force_checks_on_stream_response_references=search_agent_config.force_checks_on_stream_response_references,
        temperature=search_agent_config.temperature,
        additional_llm_options=search_agent_config.additional_llm_options,
        loop_configuration=search_agent_config.loop_configuration,
    )

    # Calculate remaining token percentages based on history percentage

    history_percent = (
        search_agent_config.token_limits.percent_of_max_tokens_for_history
    )

    agent = UniqueAIAgentConfig(
        max_loop_iterations=search_agent_config.max_loop_iterations,
        input_token_distribution=InputTokenDistributionConfig(
            percent_for_history=history_percent,
        ),
        prompt_config=prompt_config,
        services=services,
        experimental=experimental,
    )

    return UniqueAIConfig(
        space=space,
        agent=agent,
    )


def needs_conversion_to_unique_ai_space_config(
    configuration: dict[str, Any],
) -> bool:
    """Check if the configuration needs to be converted to the new UniqueAISpaceConfig."""
    if (
        "space_two_point_zero" in configuration
        or "SpaceTwoPointZeroConfig" in configuration
        or ("space" in configuration and "agent" in configuration)
    ):
        return False

    return True


if __name__ == "__main__":
    import json

    from unique_toolkit._common.utils.write_configuration import write_service_configuration

    write_service_configuration(
        service_folderpath=Path(__file__).parent.parent,
        write_folderpath=Path(__file__).parent,
        config=UniqueAIConfig(),
        sub_name="unique_ai_config",
    )

    # TODO: @cdkl Delete these models
    # This model is only used to have the old and new models in the same json
    # schema for the data migration in the node chat backend

    # The types can be generated with quicktype.io with the following command:
    # quicktype unique_ai_old_and_new_config.json \
    #   --src-lang schema --lang typescript \
    #   --just-types --prefer-types --explicit-unions \
    #   -o unique_ai_old_new_configuration.ts \
    #   --top-level UniqueAIOldAndNewConfig \
    #   --raw-type any

    # You will need to replace the `any` type with `unknown` in the generated file.
    # On the branch `feat/unique-ai-configuration-migration-node-chat-part`.
    # I you further update the types you will need to adapt both branches
    # - feat/unique-ai-configuration-migration-next-admin-part
    # - feat/unique-ai-configuration-migration-node-chat-part

    class UniqueAIOldAndNewConfig(BaseModel):
        new: UniqueAIConfig = UniqueAIConfig()
        old: SearchAgentConfig = SearchAgentConfig()

    with open(
        Path(__file__).parent / "unique_ai_old_and_new_config.json",
        "w",
    ) as f:
        json.dump(
            UniqueAIOldAndNewConfig().model_json_schema(by_alias=True),
            f,
            indent=4,
        )
