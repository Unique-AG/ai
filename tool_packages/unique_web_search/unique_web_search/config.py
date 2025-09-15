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
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.language_model.infos import ModelCapabilities
from unique_toolkit.tools.config import get_configuration_dict
from unique_toolkit.tools.schemas import BaseToolConfig

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
    Crawl4AiCrawlerConfig,
    FirecrawlCrawlerConfig,
    JinaCrawlerConfig,
    TavilyCrawlerConfig,
)
from unique_web_search.services.executors.web_search_v1_executor import RefineQueryMode
from unique_web_search.services.search_engine import (
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
        description="Whether to enable the v2 of the web search tool",
    )
    max_steps: int = Field(
        default=5,
        description="The maximum number of steps for the v2 of the web search tool",
    )
    tool_description: str = Field(
        default=TOOL_DESCRIPTIONS["v2"],
        description="The tool description for the v2 of the web search tool",
    )
    tool_description_for_system_prompt: str = Field(
        default=TOOL_DESCRIPTIONS_FOR_SYSTEM_PROMPT["v2"],
        description="The tool description for the system prompt",
    )
    tool_format_information_for_system_prompt: str = Field(
        default=DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
        description="The tool format information for the system prompt",
    )


class WebSearchV1(BaseModel):
    model_config = get_configuration_dict()

    refine_query_mode: RefineQueryMode = Field(
        default=RefineQueryMode.BASIC,
        description="The mode of the v1 of the web search tool",
    )
    max_queries: int = Field(
        default=5,
        description="The maximum number of queries for the v1 of the web search tool",
    )


class ExperimentalFeatures(FeatureExtendedSourceSerialization):
    v1_mode: WebSearchV1 = Field(
        default_factory=WebSearchV1,
        description="The mode of the v1 of the web search tool",
    )

    v2_mode: WebSearchV2 = Field(
        default_factory=WebSearchV2,
        description="The v2 of the web search tool",
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
        | SkipJsonSchema[JinaConfig]
        | SkipJsonSchema[TavilyConfig]
        | SkipJsonSchema[FireCrawlConfig]
    ) = Field(
        default_factory=GoogleConfig,
        description="Search Engine Configuration",
        discriminator="search_engine_name",
        title="Search Engine Configuration",
    )

    crawler_config: (
        Crawl4AiCrawlerConfig
        | BasicCrawlerConfig
        | FirecrawlCrawlerConfig
        | JinaCrawlerConfig
        | TavilyCrawlerConfig
    ) = Field(
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
