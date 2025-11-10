from logging import getLogger

from pydantic import BaseModel, Field, model_validator
from pydantic.json_schema import SkipJsonSchema
from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.feature_flags.schema import (
    FeatureExtendedSourceSerialization,
)
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.language_model.infos import ModelCapabilities

from unique_web_search.prompts import (
    DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
)
from unique_web_search.services.content_processing.config import (
    ContentProcessorConfig,
)
from unique_web_search.services.crawlers import (
    get_crawler_config_types_from_names,
    get_default_crawler_config,
)
from unique_web_search.services.executors.configs import (
    RefineQueryMode,
    WebSearchMode,
    WebSearchModeConfig,
    get_default_web_search_mode_config,
)
from unique_web_search.services.search_engine import (
    get_default_search_engine_config,
    get_search_engine_config_types_from_names,
)
from unique_web_search.settings import env_settings

_LOGGER = getLogger(__name__)

DEFAULT_MODEL_NAME = DEFAULT_GPT_4o

ActivatedSearchEngine = get_search_engine_config_types_from_names(
    env_settings.active_search_engines
)
DefaultSearchEngine = get_default_search_engine_config(
    env_settings.active_search_engines
)

ActivatedCrawler = get_crawler_config_types_from_names(env_settings.active_crawlers)
DefaultCrawler = get_default_crawler_config(env_settings.active_crawlers)

DEFAULT_WEB_SEARCH_MODE_CONFIG = get_default_web_search_mode_config()


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


class ExperimentalFeatures(FeatureExtendedSourceSerialization): ...


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

    web_search_mode_config: WebSearchModeConfig = Field(
        default_factory=DEFAULT_WEB_SEARCH_MODE_CONFIG,
        description="Web Search Mode Configuration",
        title="Web Search Mode Configuration",
        discriminator="mode",
    )

    search_engine_config: ActivatedSearchEngine = Field(  # type: ignore (This type is computed at runtime so pyright is not able to infer it)
        default_factory=DefaultSearchEngine,  # type: ignore (This type is computed at runtime so pyright is not able to infer it)
        description="Search Engine Configuration",
        discriminator="search_engine_name",
        title="Search Engine Configuration",
    )

    crawler_config: ActivatedCrawler = Field(  # type: ignore (This type is computed at runtime so pyright is not able to infer it)
        default_factory=DefaultCrawler,  # type: ignore (This type is computed at runtime so pyright is not able to infer it)
        title="Crawler Configuration",
        description="Crawler configuration.",
        discriminator="crawler_type",
    )

    content_processor_config: ContentProcessorConfig = Field(
        default_factory=ContentProcessorConfig,
        description="Content processor configuration",
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

    tool_format_information_for_system_prompt: str = Field(
        default=DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
        description="Tool format information for system prompt. This is used to format the tool response for the system prompt.",
    )

    experimental_features: ExperimentalFeatures = ExperimentalFeatures()

    debug: bool = Field(
        default=False,
        description="Whether to enable the debug mode",
    )

    @model_validator(mode="after")
    def disable_query_refinement_if_no_structured_output(self):
        if (
            ModelCapabilities.STRUCTURED_OUTPUT not in self.language_model.capabilities
            and self.web_search_mode_config.mode == WebSearchMode.V1
            and self.web_search_mode_config.refine_query_mode.mode
            != RefineQueryMode.DEACTIVATED
        ):
            self.web_search_mode_config.refine_query_mode.mode = (
                RefineQueryMode.DEACTIVATED
            )
            _LOGGER.warning(
                "The language model does not support structured output. Query refinement is disabled."
            )
        return self
