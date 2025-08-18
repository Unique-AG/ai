from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit.language_model import LanguageModelName



from default_language_model import DEFAULT_GPT_4o
from unique_ai.services.reference_manager.reference_manager_service import (
    ReferenceManagerConfig,
)
from unique_toolkit.unique_toolkit._common.validators import LMI
from unique_toolkit.unique_toolkit.base_agents.loop_agent.config import LoopAgentConfig
from unique_toolkit.unique_toolkit.evals.hallucination.constants import HallucinationConfig
from unique_toolkit.unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.unique_toolkit.tools.config import ToolBuildConfig, get_configuration_dict
from unique_toolkit.unique_toolkit.tools.factory import ToolFactory
from unique_toolkit.unique_toolkit.tools.schemas import BaseToolConfig


class UploadedContentConfig(BaseModel):
    model_config = get_configuration_dict()

    approximate_max_tokens_for_uploaded_content_stuff_context_window: int = Field(
        default=80_000,
        description="The approximate maximum number of tokens for uploaded content to be used in the context window before going to internal search"
        "Could trigger a too large message if not correctly combined with other tools and percent_for_history",
    )

    user_context_window_limit_warning: str = Field(
        default="The uploaded content is too large to fit into the ai model. "
        "Unique AI will search for relevant sections in the material and if needed combine the data with knowledge base content",
        description="Message to show when using the Internal Search instead of upload and chat tool due to context window limit. Jinja template.",
    )


class SearchAgentConfig(LoopAgentConfig):
    """Configure the search agent."""

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

    tools: list[ToolBuildConfig] = Field(
        default=[
            ToolBuildConfig(
                name=InternalSearchTool.name,
                configuration=InternalSearchConfig(),
            ),
            ToolBuildConfig(
                name=WebSearchTool.name,
                configuration=WebSearchConfig(),
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

    reference_manager_config: ReferenceManagerConfig | None = Field(
        default=None,
        description="The reference manager config. If None, the reference manager will not be used.",
    )

    # TODO: @gustavhartz, the Hallucination check should be triggered if enabled and the answer contains references.
    force_checks_on_stream_response_references: list[EvaluationMetricName] = (
        Field(
            default=[EvaluationMetricName.HALLUCINATION],
            description="A list of checks to force on references. This is used to add hallucination check to references without new tool calls.",
        )
    )

    uploaded_content_config: None | UploadedContentConfig = Field(
        default_factory=UploadedContentConfig,
        description="The uploaded content config.",
    )


class ReducedSearchAgentConfig(SearchAgentConfig):
    """This config is only used for the schema for the frontend"""

    project_name: SkipJsonSchema[str] = Field(
        default="Unique AI",
        description="The project name as optained from spaces 2.0",
        exclude=True,
    )

    custom_instructions: SkipJsonSchema[str] = Field(
        default="",
        description="A custom instruction provided by the system admin.",
        exclude=True,
    )

    tools: SkipJsonSchema[list[ToolBuildConfig]] = Field(
        default=[],
        exclude=True,
    )

    language_model: SkipJsonSchema[LMI] = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_0806
    )



# ------------------------------------------------------------
# Space 2.0 Config
# ------------------------------------------------------------


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

    language_model: LMI = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_0806
    )

    custom_instructions: str = Field(
        default="",
        description="A custom instruction provided by the system admin.",
    )

    tools: list[ToolBuildConfig] = Field(
        default=[
            ToolBuildConfig(
                name=InternalSearchTool.name,
                configuration=InternalSearchConfig(),
            ),
            ToolBuildConfig(
                name=WebSearchTool.name,
                configuration=WebSearchConfig(),
            ),
        ],
    )


class UniqueAISpaceConfig(SpaceConfigBase):
    """Contains configuration for the entities that a space provides."""

    type: Literal[SpaceType.UNIQUE_AI] = SpaceType.UNIQUE_AI


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

    stock_ticker_config: (
        Annotated[StockTickerConfig, Field(title="Active")] | DeactivatedNone
    ) = None

    reference_manager_config: (
        Annotated[ReferenceManagerConfig, Field(title="Active")]
        | DeactivatedNone
    ) = None

    uploaded_content_config: (
        Annotated[
            UploadedContentConfig,
            Field(title="Active"),
        ]
        | DeactivatedNone
    ) = UploadedContentConfig()


class InputTokenDistributionConfig(BaseModel):
    model_config = get_configuration_dict(frozen=True)

    percent_for_history: float = Field(
        default=0.6,
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
        description="The temperature to use for the LLM.",
    )

    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the LLM.",
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
        reference_manager_config=search_agent_config.reference_manager_config,
        uploaded_content_config=search_agent_config.uploaded_content_config,
    )

    experimental = ExperimentalConfig(
        thinking_steps_display=search_agent_config.thinking_steps_display,
        force_checks_on_stream_response_references=search_agent_config.force_checks_on_stream_response_references,
        temperature=search_agent_config.temperature,
        additional_llm_options=search_agent_config.additional_llm_options,
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

    from _common.utils.write_configuration import write_service_configuration

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
