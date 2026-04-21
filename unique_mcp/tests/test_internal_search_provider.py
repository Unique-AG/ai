from __future__ import annotations

from types import SimpleNamespace

import pytest

from unique_mcp.context_requirements import CONTEXT_REQUIREMENTS_META_KEY
from unique_mcp.internal_search.config import (
    ChatInternalSearchMcpConfig,
    KnowledgeBaseInternalSearchMcpConfig,
)
from unique_mcp.internal_search.meta import InternalSearchRequestMeta
from unique_mcp.internal_search.provider import (
    ChatInternalSearchToolProvider,
    KnowledgeBaseInternalSearchToolProvider,
    _format_tool_result,
)
from unique_mcp.meta_keys import MetaKeys

# Deferred import — importing InternalSearchState pulls the unique-toolkit
# internal-search package which is not required for every test here.
from unique_toolkit.components.internal_search.base.schemas import InternalSearchState  # noqa: E402
from unique_toolkit.components.internal_search.knowledge_base.schemas import (  # noqa: E402
    KnowledgeBaseInternalSearchState,
)
from unique_toolkit.content.schemas import ContentChunk  # noqa: E402


@pytest.mark.ai
def test_chat_provider__populate_state_sets_content_ids():
    service = SimpleNamespace(state=InternalSearchState(search_queries=[]))
    request_meta = InternalSearchRequestMeta.from_request_meta(
        {
            MetaKeys.SELECTED_UPLOADED_FILE_IDS: ["file-1", "file-2"],
            MetaKeys.LANGUAGE_MODEL_MAX_INPUT_TOKENS: 128000,
        }
    )

    service.state.search_queries = ["alpha", "beta"]
    service.state.content_ids = request_meta.chat_content_ids
    service.state.language_model_max_input_tokens = 128000
    service.state.language_model_info = object()

    assert service.state.search_queries == ["alpha", "beta"]
    assert service.state.content_ids == ["file-1", "file-2"]
    assert service.state.language_model_info is not None
    assert service.state.language_model_max_input_tokens == 128000


@pytest.mark.ai
def test_kb_provider__populate_state_sets_content_ids_and_metadata_override():
    service = SimpleNamespace(
        state=KnowledgeBaseInternalSearchState(search_queries=[]),
    )
    request_meta = InternalSearchRequestMeta.from_request_meta(
        {
            MetaKeys.CONTENT_IDS: ["doc-1"],
            MetaKeys.METADATA_FILTER: {"kind": "policy"},
        }
    )

    service.state.search_queries = ["policy"]
    service.state.content_ids = request_meta.knowledge_base_content_ids
    service.state.metadata_filter_override = request_meta.metadata_filter

    assert service.state.search_queries == ["policy"]
    assert service.state.content_ids == ["doc-1"]
    assert service.state.metadata_filter_override == {"kind": "policy"}


@pytest.mark.ai
def test_provider__format_result_returns_chunk_text_and_meta():
    chunk = ContentChunk(chunk_id="c1", text="chunk text", start_page=1, end_page=1)
    result = _format_tool_result(
        config=KnowledgeBaseInternalSearchMcpConfig(),
        result=SimpleNamespace(
            chunks=[chunk],
            debug_info={"searchStrings": ["chunk"]},
        ),
    )

    assert result.content[0].text == "chunk text"
    assert result.content[0].meta["chunk"]["chunk_id"] == "c1"


@pytest.mark.ai
def test_chat_config_default_tool_meta_includes_context_requirements():
    config = ChatInternalSearchMcpConfig()

    reqs = config.tool_meta[CONTEXT_REQUIREMENTS_META_KEY]
    assert isinstance(reqs, dict)
    assert MetaKeys.CHAT_ID in reqs["required"]
    assert MetaKeys.USER_ID in reqs["required"]
    assert MetaKeys.CONTENT_IDS in reqs["optional"]


@pytest.mark.ai
def test_kb_config_default_tool_meta_includes_context_requirements():
    config = KnowledgeBaseInternalSearchMcpConfig()

    reqs = config.tool_meta[CONTEXT_REQUIREMENTS_META_KEY]
    assert isinstance(reqs, dict)
    assert MetaKeys.USER_ID in reqs["required"]
    assert MetaKeys.COMPANY_ID in reqs["required"]
    assert MetaKeys.CHAT_ID not in reqs["required"]


@pytest.mark.ai
def test_providers_can_be_constructed_without_context_provider():
    ChatInternalSearchToolProvider(config=ChatInternalSearchMcpConfig())
    KnowledgeBaseInternalSearchToolProvider(
        config=KnowledgeBaseInternalSearchMcpConfig()
    )
