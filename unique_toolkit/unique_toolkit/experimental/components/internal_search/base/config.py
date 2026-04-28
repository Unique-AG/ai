from typing import Any

from pydantic import BaseModel, Field, model_validator

from unique_toolkit._common.config_checker import register_config
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.content.schemas import ContentSearchType

_FIELD_ALIASES: dict[str, str] = {
    "ftsSearchLanguage": "searchLanguage",
}

# 200 matches the tool's sort-enabled default — conservative by design.
# Callers who need higher recall (e.g. multi-query with post-processing) should set
# limit explicitly in config. The service does not cap by token budget; that is the
# post-processor's job via pick_content_chunks_for_token_window.
DEFAULT_LIMIT = 200


# TODO [UN-17521]: remove _remap_legacy_fields once ftsSearchLanguage is fully migrated
@register_config()
class InternalSearchConfig(BaseModel):
    """Retrieval-only config. Token budgeting, reranking and sorting live in PostProcessorConfig."""

    model_config = get_configuration_dict()

    @model_validator(mode="before")
    @classmethod
    def _remap_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for old_key, new_key in _FIELD_ALIASES.items():
                if old_key in data and new_key not in data:
                    data[new_key] = data.pop(old_key)
        return data

    # ── Retrieval ─────────────────────────────────────────────────────────────
    search_type: ContentSearchType = Field(
        default=ContentSearchType.COMBINED,
        description="The type of search to perform. Two possible values: `COMBINED` or `VECTOR`.",
    )
    search_language: str = Field(
        default="english",
        description="The language to use for the search.",
    )
    score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score threshold to filter chunks on relevancy.",
    )
    limit: int = Field(
        default=DEFAULT_LIMIT,
        description=(
            "Maximum number of chunks to return per search query. "
            "Default is 200 — the conservative baseline. Increase for higher recall "
            "when a post-processor with token windowing follows."
        ),
    )

    # ── Multi-query ───────────────────────────────────────────────────────────
    max_search_strings: int = Field(
        default=10,
        ge=1,
        description="The maximum number of search strings to perform in a single tool call.",
    )
    enable_multiple_search_strings_execution: bool = Field(
        default=True,
        description="Allow execution of multiple search strings in one call.",
    )


__all__ = [
    "InternalSearchConfig",
    "DEFAULT_LIMIT",
]
