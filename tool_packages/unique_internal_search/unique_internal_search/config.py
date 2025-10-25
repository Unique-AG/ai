from typing import Annotated, Any

from pydantic import (
    AliasChoices,
    Field,
)
from pydantic.json_schema import SkipJsonSchema
from unique_internal_search.schema import (
    ChunkMetadataSection,
)
from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit._common.feature_flags.schema import (
    FeatureExtendedSourceSerialization,
)
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.history_manager.history_manager import DeactivatedNone
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.agentic.tools.utils.source_handling.schema import SourceFormatConfig
from unique_toolkit.content.schemas import (
    ContentRerankerConfig,
    ContentSearchType,
)

from unique_internal_search.prompts import (
    DEFAULT_LANGUAGE_PARAM_DESCRIPTION,
    DEFAULT_SEARCH_STRING_PARAM_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION,
    DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
    DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
)
from unique_internal_search.validators import get_string_field_with_pattern_validation


class ExperimentalFeatures(FeatureExtendedSourceSerialization): ...


DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_ENABLED = 200
DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_DISABLED = 1000


def _search_limit_factory(data: dict[str, Any]) -> int:
    return (
        DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_ENABLED
        if data["chunk_relevancy_sort_config"].enabled
        else DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_DISABLED
    )


class InternalSearchConfig(BaseToolConfig):
    search_type: ContentSearchType = Field(
        default=ContentSearchType.COMBINED,
        description="The type of search to perform. Two possible values: `COMBINED` or `VECTOR`.",
    )
    max_tokens_for_sources: SkipJsonSchema[int] = (
        Field(  # TODO: Remove SkipJsonSchema once UI (Spaces 2.0) can be configured to not include certain fields
            default=30_000,
            description="The maximum number of tokens to use for the sources.",
        )
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
    scope_ids: Annotated[list[str], Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="The scope ids to use for the search.",
    )
    scope_to_chat_on_upload: bool = Field(
        default=False,
        description="Whether to scope the search should be limited to files uploaded within the chat session when uploaded files are present.",
    )
    chunked_sources: bool = Field(
        default=True,
        description="Whether each chunk is added as an individual source in the final LLM prompt. If set to False, all chunks from the same document are combined into a single source.",
    )
    reranker_config: (
        Annotated[ContentRerankerConfig, Field(title="Active")] | DeactivatedNone
    ) = Field(
        default=None,
        description="The reranker config to use for the search.",
    )
    search_language: str = Field(
        default="english",
        validation_alias=AliasChoices("ftsSearchLanguage", "searchLanguage"),
        description="The language to use for the search.",
    )
    # evaluation_config: EvaluationMetricConfig = EvaluationMetricConfig()
    chunk_relevancy_sort_config: ChunkRelevancySortConfig = Field(
        default_factory=ChunkRelevancySortConfig,
        description="The chunk relevancy sort config to use for the search.",
    )
    limit: int = Field(
        default_factory=_search_limit_factory,
        description="The limit of chunks to return.",
    )
    chat_only: bool = Field(
        default=False,
        description="Whether to only chat on the upload.",
    )

    tool_description: str = get_string_field_with_pattern_validation(
        DEFAULT_TOOL_DESCRIPTION,
        description="Tool description.",
    )
    param_description_search_string: str = get_string_field_with_pattern_validation(
        DEFAULT_SEARCH_STRING_PARAM_DESCRIPTION,
        description="`search_string` parameter description.",
    )
    param_description_language: str = get_string_field_with_pattern_validation(
        DEFAULT_LANGUAGE_PARAM_DESCRIPTION,
        description="`language` parameter description.",
    )
    tool_description_for_system_prompt: str = get_string_field_with_pattern_validation(
        DEFAULT_TOOL_DESCRIPTION_FOR_SYSTEM_PROMPT,
        description="Tool description for the system prompt.",
    )
    tool_format_information_for_system_prompt: str = (
        get_string_field_with_pattern_validation(
            DEFAULT_TOOL_FORMAT_INFORMATION_FOR_SYSTEM_PROMPT,
            description="Tool format information for the system prompt.",
        )
    )
    evaluation_check_list: list[EvaluationMetricName] = Field(
        default=[EvaluationMetricName.HALLUCINATION],
        description="The list of evaluation metrics to check.",
    )
    experimental_features: SkipJsonSchema[ExperimentalFeatures] = ExperimentalFeatures()

    source_format_config: SkipJsonSchema[SourceFormatConfig] = SourceFormatConfig()

    metadata_sections: list[ChunkMetadataSection] = Field(
        default=[],
        description="Metadata sections to add to the search results chunks.",
    )

    score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="The score threshold to use for the search to filter chunks on relevancy.",
    )
    exclude_uploaded_files: bool = Field(
        default=False,
        description="Whether to exclude uploaded files from the search. Overrides the `chat_only` parameter as it removes the `chat_id` from the search.",
    )
