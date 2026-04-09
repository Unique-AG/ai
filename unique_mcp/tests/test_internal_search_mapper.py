from __future__ import annotations

import pytest

from unique_mcp.internal_search.config import (
    ChatInternalSearchMcpConfig,
    KnowledgeBaseInternalSearchMcpConfig,
)
from unique_mcp.internal_search.mapper import map_legacy_internal_search_config


@pytest.mark.ai
def test_map_legacy_internal_search_config__chat_discards_kb_only_fields():
    config = map_legacy_internal_search_config(
        {
            "tool_description": "Chat search tool",
            "param_description_search_string": "Query uploaded files",
            "scope_ids": ["kb-1"],
            "search_type": "VECTOR",
        },
        target="chat",
    )

    assert isinstance(config, ChatInternalSearchMcpConfig)
    assert config.description == "Chat search tool"
    assert config.param_description_search_string == "Query uploaded files"
    assert not hasattr(config.execution_config, "scope_ids")
    assert config.execution_config.search_type == "VECTOR"


@pytest.mark.ai
def test_map_legacy_internal_search_config__kb_keeps_scope_ids_and_aliases():
    config = map_legacy_internal_search_config(
        {
            "tool_description": "KB search tool",
            "scope_ids": ["kb-1", "kb-2"],
            "ftsSearchLanguage": "german",
        },
        target="knowledge_base",
    )

    assert isinstance(config, KnowledgeBaseInternalSearchMcpConfig)
    assert config.description == "KB search tool"
    assert config.execution_config.scope_ids == ["kb-1", "kb-2"]
    assert config.execution_config.search_language == "german"
