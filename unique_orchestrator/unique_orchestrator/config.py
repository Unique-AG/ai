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
from unique_internal_search.uploaded_search.config import (
    UploadedSearchConfig,
)
from unique_stock_ticker.config import StockTickerConfig
from unique_swot import SwotAnalysisTool, SwotAnalysisToolConfig
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
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
    QWEN_MAX_LOOP_ITERATIONS,
    PlanningConfig,
)
from unique_toolkit.agentic.tools.a2a import (
    REFERENCING_INSTRUCTIONS_FOR_SYSTEM_PROMPT,
    REFERENCING_INSTRUCTIONS_FOR_USER_PROMPT,
)
from unique_toolkit.agentic.tools.a2a.evaluation import SubAgentEvaluationServiceConfig
from unique_toolkit.agentic.tools.experimental.open_file_tool.config import (
    OpenFileToolConfig,
)
from unique_toolkit.agentic.tools.experimental.retrieve_search_scope_tool import (
    RetrieveSearchScopeConfig,
    RetrieveSearchScopeTool,
)
from unique_toolkit.agentic.tools.experimental.todo import (
    TodoConfig,
    TodoWriteTool,
)
from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.tool import ToolBuildConfig
from unique_toolkit.agentic.tools.tool_progress_reporter import (
    ToolProgressReporterConfig,
)
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import LanguageModelName, ModelCapabilities
from unique_user_memory.config import UserMemoryConfig
from unique_web_search.config import WebSearchConfig
from unique_web_search.service import WebSearchTool

from unique_orchestrator.settings import env_settings

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


class SwitchableLanguageModelConfig(BaseToolConfig):
    """A language model that chat users may select for a single message."""

    display_name: str = Field(
        description="Human-readable label shown to chat users in the model picker.",
    )
    language_model: LMI = Field(
        description=(
            "Language-model configuration accepted from the platform payload as "
            "`languageModel`."
        ),
    )


class SpaceConfigBase(BaseToolConfig, Generic[T]):
    """Base class for space configuration."""

    type: T = Field(description="The type of the space.")

    project_name: str = Field(
        default="Unique AI",
        description="The project name as optained from spaces 2.0",
    )

    language_model: LMI = get_LMI_default_field(DEFAULT_GPT_4o)

    allow_model_switching: bool = Field(
        default=False,
        description=(
            "Whether chat users may override the language model for a single message"
        ),
    )

    allow_user_memory: bool = Field(
        default=False,
        description=("Whether persistent per-user memory is active for this space."),
    )

    switchable_language_models: list[SwitchableLanguageModelConfig] = Field(
        default_factory=list,
        description=("Language models selectable by chat users for a single message."),
    )

    custom_instructions: str = Field(
        default="",
        description="A custom instruction provided by the system admin.",
    )

    user_space_instructions: str | None = Field(
        default=None,
        description="User instructions for the space provided by the user.",
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
            if tool.name in (
                InternalSearchTool.name,
                WebSearchTool.name,
                RetrieveSearchScopeTool.name,
            ):
                tool.configuration.language_model_max_input_tokens = (  # type: ignore
                    info.data["language_model"].token_limits.token_limit_input
                )
        return tools


class UniqueAISpaceConfig(SpaceConfigBase):
    """Contains configuration for the entities that a space provides."""

    type: Literal[SpaceType.UNIQUE_AI] = SpaceType.UNIQUE_AI


UniqueAISpaceConfig.model_rebuild()


_MODEL_FAMILIES = ("qwen", "mistral")


def get_model_family(model_name: str) -> str | None:
    name = model_name.lower()
    for family in _MODEL_FAMILIES:
        if family in name:
            return family
    return None


class QwenConfig(BaseToolConfig):
    """Qwen specific configuration."""

    max_loop_iterations: Annotated[
        int, *ClipInt(min_value=1, max_value=env_settings.limit_max_loop_iterations)
    ] = Field(
        default=QWEN_MAX_LOOP_ITERATIONS,
        description="Maximum number of agentic loop iterations for Qwen models.",
    )

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
        *ClipInt(
            min_value=1, max_value=env_settings.limit_max_tool_calls_per_iteration
        ),
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
    system_prompt_template: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=25),
    ] = Field(
        default_factory=lambda: (
            Path(__file__).parent / "prompts" / "system_prompt.jinja2"
        ).read_text(),
        description="The system prompt template as a Jinja2 template string.",
    )

    user_message_prompt_template: Annotated[
        str,
        RJSFMetaTag.StringWidget.textarea(rows=4),
    ] = Field(
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

    user_memory_config: Annotated[UserMemoryConfig, RJSFMetaTag.SpecialWidget.hidden()] = Field(
        title="User Memory",
        description="Configuration for persistent user memory.",
        default_factory=UserMemoryConfig,
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
    def check_if_follow_up_questions_config_is_none(cls, follow_up_questions_config):
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


class HistoryConfig(BaseToolConfig):
    percent_for_history: float = Field(
        default=0.2,
        ge=0.0,
        lt=1.0,
        description="The fraction of the max input tokens that will be reserved for the history.",
    )

    enable_tool_call_persistence: bool = Field(
        default=False,
        description="Persist tool calls and reconstruct tool call history across turns.",
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


class ResponsesApiConfig(BaseToolConfig):
    use_responses_api: bool = Field(
        default=False,
        description="If set, the main agent will use the Responses API from OpenAI",
    )


class UploadedSearchToolConfig(BaseToolConfig):
    force: bool = Field(
        default=True,
        title="Force tool",
        description="If set, the tool will be forced when the user uploads a file",
    )
    tool_config: UploadedSearchConfig = UploadedSearchConfig()

    @model_validator(mode="after")
    def validate_tool_config(self) -> "UploadedSearchToolConfig":
        self.tool_config.enable_tool_call_system_reminder = self.force
        return self


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

    responses_api_config: SkipJsonSchema[ResponsesApiConfig] = ResponsesApiConfig()

    open_file_tool_config: OpenFileToolConfig = OpenFileToolConfig()

    retrieve_search_scope_config: RetrieveSearchScopeConfig = (
        RetrieveSearchScopeConfig()
    )
    todo_config: TodoConfig = Field(
        title="Todo Tool",
        description="Configuration for the todo tool",
        default_factory=TodoConfig,
    )

    uploaded_search_tool_config: UploadedSearchToolConfig = UploadedSearchToolConfig()

    use_responses_api: bool = Field(
        default=False,
        description="If set, the main agent will use the Responses API from OpenAI",
    )


class UniqueAIAgentConfig(BaseToolConfig):
    max_loop_iterations: Annotated[
        int, *ClipInt(min_value=1, max_value=env_settings.limit_max_loop_iterations)
    ] = 20

    input_token_distribution: HistoryConfig = Field(
        default=HistoryConfig(),
        title="Loop History",
        description="Configuration for loop history.",
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

    @model_validator(mode="after")
    def remove_tools_with_unsupported_model_capabilities(self) -> "UniqueAIConfig":
        if ModelCapabilities.RESPONSES_API in self.space.language_model.capabilities:
            return self

        self.space.tools = [
            tool
            for tool in self.space.tools
            if tool.name != OpenAIBuiltInToolName.CODE_INTERPRETER
        ]
        return self

    @model_validator(mode="after")
    def disable_responses_api_when_model_does_not_support_it(self) -> "UniqueAIConfig":
        if ModelCapabilities.RESPONSES_API in self.space.language_model.capabilities:
            return self

        self.agent.experimental.responses_api_config.use_responses_api = False
        self.agent.experimental.use_responses_api = False
        return self

    @model_validator(mode="after")
    def enable_responses_api_for_code_interpreter_tool(self) -> "UniqueAIConfig":
        """Auto-enable the Responses API when Code Interpreter is added directly as a tool.

        When Code Interpreter is configured via the UI tool selector (i.e. as an entry in
        space.tools), neither `use_responses_api` nor `responses_api_config.code_interpreter`
        are set.  This validator detects that combination and fills in the required defaults so
        that `unique_ai_builder` routes the request correctly and registers all postprocessors.

        The validator only activates when the selected model actually supports the Responses API;
        models that do not support it are left untouched so that an invalid configuration is not
        silently promoted.
        """
        # Only consider enabled tools — a disabled entry (toggle off) means the user
        # has not intentionally activated Code Interpreter via the UI toggle.
        tool_names = [tool.name for tool in self.space.tools if tool.is_enabled]
        model_supports_responses_api = (
            ModelCapabilities.RESPONSES_API in self.space.language_model.capabilities
        )

        if (
            OpenAIBuiltInToolName.CODE_INTERPRETER in tool_names
            and model_supports_responses_api
        ):
            self.agent.experimental.responses_api_config.use_responses_api = True

        return self

    @model_validator(mode="after")
    def enable_responses_api_for_gpt_55_and_gpt_55_pro(self) -> "UniqueAIConfig":
        """Auto-enable the Responses API for GPT-5.5 (AZURE_GPT_55_2026_0424) and GPT-5.5-Pro (AZURE_GPT_55_PRO_2026_0424).

        TEMP FIX: gpt-5.5-2026-04-24 and gpt-5.5-pro-2026-04-24 reject requests that combine `tools` with
        `reasoning_effort` on /v1/chat/completions and demands /v1/responses.
        Forcing the Responses API here avoids the OpenAI 400 error until the
        runner can pick the right transport based on model capabilities.
        Tracked in Jira: UN-20123.
        """
        if (
            self.space.language_model.name == LanguageModelName.AZURE_GPT_55_2026_0424
            or self.space.language_model.name
            == LanguageModelName.AZURE_GPT_55_PRO_2026_0424
        ):
            self.agent.experimental.responses_api_config.use_responses_api = True
        return self

    @model_validator(mode="after")
    def validate_open_file_tool_requires_responses_api(self) -> "UniqueAIConfig":
        uses_responses_api = (
            self.agent.experimental.responses_api_config.use_responses_api
            or self.agent.experimental.use_responses_api
        )
        if (
            self.agent.experimental.open_file_tool_config.enabled
            and not uses_responses_api
        ):
            raise ValueError(
                "open_file_tool_config.enabled requires the Responses API to be enabled."
            )
        return self

    @model_validator(mode="after")
    def inject_retrieve_search_scope_tool(self) -> "UniqueAIConfig":
        tool_names = [t.name for t in self.space.tools]
        has_tool = RetrieveSearchScopeTool.name in tool_names
        config = self.agent.experimental.retrieve_search_scope_config

        if config.enabled and not has_tool:
            config.language_model_max_input_tokens = (
                self.space.language_model.token_limits.token_limit_input
            )
            self.space.tools.append(
                ToolBuildConfig(
                    name=RetrieveSearchScopeTool.name,
                    display_name=RetrieveSearchScopeTool.default_display_name,
                    configuration=config,
                )
            )
        elif not config.enabled and has_tool:
            self.space.tools = [
                t for t in self.space.tools if t.name != RetrieveSearchScopeTool.name
            ]

        return self

    @model_validator(mode="after")
    def inject_todo_tool(self) -> "UniqueAIConfig":
        tool_names = [t.name for t in self.space.tools]
        has_tool = TodoWriteTool.name in tool_names
        config = self.agent.experimental.todo_config

        if config.enabled and not has_tool:
            self.space.tools.append(
                ToolBuildConfig(
                    name=TodoWriteTool.name,
                    display_name=config.display_name,
                    configuration=config,
                )
            )
        elif not config.enabled and has_tool:
            self.space.tools = [
                t for t in self.space.tools if t.name != TodoWriteTool.name
            ]

        return self

    @property
    def effective_max_loop_iterations(self) -> int:
        """Effective max loop iterations, accounting for model-specific overrides."""
        family = get_model_family(str(self.space.language_model))
        if family == "qwen":
            return self.agent.experimental.loop_configuration.model_specific.qwen.max_loop_iterations
        return self.agent.max_loop_iterations
