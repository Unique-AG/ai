from logging import getLogger

from pydantic import BaseModel, Field, model_validator
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.default_language_model import DEFAULT_GPT_4o
from unique_toolkit._common.feature_flags.schema import (
    FeatureExtendedSourceSerialization,
)
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.language_model.infos import ModelCapabilities

from unique_web_search.prompts import (
    DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
    REFINE_QUERY_SYSTEM_PROMPT,
    RESTRICT_DATE_DESCRIPTION,
    TOOL_DESCRIPTIONS,
    TOOL_DESCRIPTIONS_FOR_SYSTEM_PROMPT,
)
from unique_web_search.services.content_processing.config import (
    ContentProcessorConfig,
)
from unique_web_search.services.crawlers import (
    BasicCrawlerConfig,
    CrawlerConfigTypes,
)
from unique_web_search.services.executors.web_search_v1_executor import RefineQueryMode
from unique_web_search.services.search_engine import (
    BingSearchConfig,
    BraveSearchConfig,
    FireCrawlConfig,
    GoogleConfig,
    JinaConfig,
    TavilyConfig,
)

logger = getLogger(__name__)

DEFAULT_MODEL_NAME = DEFAULT_GPT_4o


class AnswerGenerationConfig(BaseModel):
    model_config = get_configuration_dict()
    limit_token_sources: int = Field(
        default=10000,
        description="Token Source Limit",
    )
    max_chunks_to_consider: int = Field(
        default=20,
        description="Token Source Limit",
    )
    number_history_interactions_included: int = Field(
        default=2,
        description="Number of history interactions included",
    )


class WebSearchV2(BaseModel):
    model_config = get_configuration_dict()

    enabled: bool = Field(
        default=False,
        description="Enable or disable the WebSearch V2 tool. Set to True to activate the step-based web search executor.",
    )
    max_steps: int = Field(
        default=5,
        description="Maximum number of sequential steps (searches or URL reads) allowed in a single WebSearch V2 plan.",
    )
    tool_description: str = Field(
        default=TOOL_DESCRIPTIONS["v2"],
        description="Information to help the language model decide when to select this tool; describes the tool's general purpose and when it is relevant.",
    )
    tool_description_for_system_prompt: str = Field(
        default=TOOL_DESCRIPTIONS_FOR_SYSTEM_PROMPT["v2"],
        description="Description of the tool's capabilities, intended for inclusion in system prompts to inform the language model what the tool can do.",
    )
    tool_format_information_for_system_prompt: str = Field(
        default=DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
        description="Instructions for the language model on how to reference and organize information from the tool in its response.",
    )


class WebSearchV1(BaseModel):
    model_config = get_configuration_dict()

    refine_query_mode: RefineQueryMode = Field(
        default=RefineQueryMode.BASIC,
        description="Query refinement strategy for WebSearch V1. Determines how user queries are improved before searching (e.g., BASIC, ADVANCED).",
    )
    max_queries: int = Field(
        default=5,
        description="Maximum number of search queries that WebSearch V1 will issue per user request.",
    )


class ExperimentalFeatures(FeatureExtendedSourceSerialization):
    v1_mode: WebSearchV1 = Field(
        default_factory=WebSearchV1,
        description=(
            "Configuration options for WebSearch V1 mode. "
            "Controls the behavior and parameters of the original web search tool, "
            "including query refinement and search limits."
        ),
    )

    v2_mode: WebSearchV2 = Field(
        default_factory=WebSearchV2,
        description=(
            "Configuration options for WebSearch V2 mode. "
            "Enables and customizes the new step-based web search executor, "
            "allowing for advanced planning and multi-step research workflows."
        ),
    )


class QueryRefinementConfig(BaseModel):
    model_config = get_configuration_dict()
    enabled: bool = Field(
        default=True,
        description="Whether to enable the refined query",
    )
    system_prompt: str = Field(
        default=REFINE_QUERY_SYSTEM_PROMPT,
        description="The system prompt to refine the query",
    )


class WebSearchToolParametersConfig(BaseModel):
    model_config = get_configuration_dict()
    query_description: str = Field(
        default="The search query to issue to the web.",
        description="The tool parameter query description",
    )
    date_restrict_description: str = Field(
        default=RESTRICT_DATE_DESCRIPTION,
        description="The tool parameter date restrict description",
    )


class WebSearchConfig(BaseToolConfig):
    language_model: LMI = get_LMI_default_field(DEFAULT_MODEL_NAME)

    limit_token_sources: SkipJsonSchema[int] = Field(
        default=60_000,  # TODO: Remove SkipJsonSchema once UI (Spaces 2.0) can be configured to not include certain fields
        description="Token Source Limit",
    )
    percentage_of_input_tokens_for_sources: float = Field(
        default=0.4,
        description="The percentage of the maximum input tokens of the language model to use for the tool response.",
        ge=0.0,
        le=1.0,
    )
    language_model_max_input_tokens: SkipJsonSchema[int | None] = Field(
        default=None,
        description="Language model maximum input tokens",
    )

    search_engine_config: (
        GoogleConfig
        | BingSearchConfig
        | BraveSearchConfig
        | SkipJsonSchema[JinaConfig]
        | SkipJsonSchema[TavilyConfig]
        | SkipJsonSchema[FireCrawlConfig]
    ) = Field(
        default_factory=GoogleConfig,
        description="Search Engine Configuration",
        discriminator="search_engine_name",
        title="Search Engine Configuration",
    )

    crawler_config: CrawlerConfigTypes = Field(
        default_factory=BasicCrawlerConfig,
        description="The crawler configuration.",
        discriminator="crawler_type",
    )

    content_processor_config: ContentProcessorConfig = Field(
        default_factory=ContentProcessorConfig,
        description="The content processor configuration",
        title="Content Processor Configuration",
    )

    chunk_relevancy_sort_config: ChunkRelevancySortConfig = Field(
        default_factory=ChunkRelevancySortConfig,
        description="Chunk Relevancy Sort Configuration",
        title="Chunk Relevancy Sort Configuration",
    )

    evaluation_check_list: list[EvaluationMetricName] = Field(
        default=[
            EvaluationMetricName.HALLUCINATION,
        ],
        description="Check list of evaluations executed conditionally after the answer is generated",
        title="Evaluation Check List",
    )

    query_refinement_config: QueryRefinementConfig = Field(
        default_factory=QueryRefinementConfig,
        description="The query refinement configuration",
        title="Query Refinement Configuration",
    )

    tool_parameters_config: WebSearchToolParametersConfig = Field(
        default_factory=WebSearchToolParametersConfig,
        description="The tool parameters configuration",
        title="Tool Parameters Configuration",
    )

    tool_description: str = Field(
        default=TOOL_DESCRIPTIONS["v1"],
        description="The tool description",
    )

    tool_description_for_system_prompt: str = Field(
        default=TOOL_DESCRIPTIONS_FOR_SYSTEM_PROMPT["v1"],
    )

    tool_format_information_for_system_prompt: str = Field(
        default=DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
    )

    experimental_features: ExperimentalFeatures = ExperimentalFeatures()

    debug: bool = Field(
        default=False,
        description="Whether to enable the debug mode",
    )

    @model_validator(mode="after")
    def disable_query_refinement_if_no_structured_output(self):
        if ModelCapabilities.STRUCTURED_OUTPUT not in self.language_model.capabilities:
            self.query_refinement_config.enabled = False
            logger.warning(
                "The language model does not support structured output. Query refinement is disabled."
            )
        return self
