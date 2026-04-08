from logging import getLogger
from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit._common.chunk_relevancy_sorter.config import (
    ChunkRelevancySortConfig,
)
from unique_toolkit.agentic.history_manager.history_manager import DeactivatedNone
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.content.schemas import ContentRerankerConfig, ContentSearchType

DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_ENABLED = 200
DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_DISABLED = 1000
_LOGGER = getLogger(__name__)

_FIELD_ALIASES: dict[str, str] = {
    "ftsSearchLanguage": "searchLanguage",
}


def _search_limit_factory(data: dict[str, Any]) -> int:
    return (
        DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_ENABLED
        if data["chunk_relevancy_sort_config"].enabled
        else DEFAULT_LIMIT_CHUNK_RELEVANCY_SORT_DISABLED
    )


# TODO [UN-17521]: remove _remap_legacy_fields once ftsSearchLanguage is fully migrated
class InternalSearchConfig(BaseModel):
    """Execution-only search config. No tool UI, prompts, or evaluation fields."""

    model_config = get_configuration_dict()

    @model_validator(mode="before")
    @classmethod
    def _remap_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for old_key, new_key in _FIELD_ALIASES.items():
                if old_key in data and new_key not in data:
                    data[new_key] = data.pop(old_key)
        return data

    search_type: ContentSearchType = Field(
        default=ContentSearchType.COMBINED,
        description="The type of search to perform. Two possible values: `COMBINED` or `VECTOR`.",
    )
    max_tokens_for_sources: SkipJsonSchema[int] = Field(
        default=30_000,
        description="The maximum number of tokens to use for the sources.",
    )
    percentage_of_input_tokens_for_sources: float = Field(
        default=0.4,
        description="The percentage of the maximum input tokens of the language model to use for the tool response.",
        ge=0.0,
        le=1.0,
    )
    scope_ids: Annotated[list[str], Field(title="Active")] | DeactivatedNone = Field(
        default=None,
        description="The scope ids to use for the search.",
    )
    chunked_sources: bool = Field(
        default=True,
        description="Whether each chunk is added as an individual source. If False, chunks from the same document are merged.",
    )
    reranker_config: (
        Annotated[ContentRerankerConfig, Field(title="Active")] | DeactivatedNone
    ) = Field(
        default=None,
        description="The reranker config to use for the search.",
    )
    search_language: str = Field(
        default="english",
        description="The language to use for the search.",
    )
    chunk_relevancy_sort_config: ChunkRelevancySortConfig = Field(
        default_factory=ChunkRelevancySortConfig,
        description="The chunk relevancy sort config to use for the search.",
    )
    limit: int = Field(
        default_factory=_search_limit_factory,
        description="The limit of chunks to return.",
    )
    enable_multiple_search_strings_execution: bool = Field(
        default=True,
        description="Allow execution of multiple search strings in one call.",
    )
    score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score threshold to filter chunks on relevancy.",
    )
    max_search_strings: int = Field(
        default=10,
        ge=1,
        description="The maximum number of search strings to perform in a single tool call.",
    )
