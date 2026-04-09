from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, cast

from pydantic import BaseModel

from unique_mcp.internal_search.config import (
    ChatInternalSearchMcpConfig,
    KnowledgeBaseInternalSearchMcpConfig,
)

_COMMON_EXECUTION_KEYS = {
    "search_type",
    "max_tokens_for_sources",
    "percentage_of_input_tokens_for_sources",
    "chunked_sources",
    "reranker_config",
    "search_language",
    "chunk_relevancy_sort_config",
    "limit",
    "enable_multiple_search_strings_execution",
    "score_threshold",
    "max_search_strings",
    "ftsSearchLanguage",
}
_KB_EXECUTION_KEYS = {"scope_ids"}


def _normalise_legacy_config(
    legacy_config: Mapping[str, object] | BaseModel,
) -> dict[str, object]:
    if isinstance(legacy_config, BaseModel):
        return cast(
            dict[str, object],
            legacy_config.model_dump(by_alias=True, exclude_none=True),
        )
    return dict(legacy_config)


def map_legacy_internal_search_config(
    legacy_config: Mapping[str, object] | BaseModel,
    *,
    target: Literal["chat", "knowledge_base"],
) -> ChatInternalSearchMcpConfig | KnowledgeBaseInternalSearchMcpConfig:
    legacy_data = _normalise_legacy_config(legacy_config)
    tool_kwargs: dict[str, object] = {}
    if "tool_description" in legacy_data:
        tool_kwargs["description"] = legacy_data["tool_description"]
    if "param_description_search_string" in legacy_data:
        tool_kwargs["param_description_search_string"] = legacy_data[
            "param_description_search_string"
        ]

    execution_data = {
        key: legacy_data[key] for key in _COMMON_EXECUTION_KEYS if key in legacy_data
    }

    if target == "chat":
        return ChatInternalSearchMcpConfig.model_validate(
            {
                **tool_kwargs,
                "execution_config": execution_data,
            }
        )

    execution_data.update(
        {key: legacy_data[key] for key in _KB_EXECUTION_KEYS if key in legacy_data}
    )
    return KnowledgeBaseInternalSearchMcpConfig.model_validate(
        {
            **tool_kwargs,
            "execution_config": execution_data,
        }
    )


__all__ = ["map_legacy_internal_search_config"]
