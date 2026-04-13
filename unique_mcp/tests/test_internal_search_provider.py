from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from mcp.types import TextContent
from pydantic import SecretStr
from unique_toolkit.app.unique_settings import (
    AuthContext,
    UniqueApi,
    UniqueApp,
    UniqueSettings,
)
from unique_toolkit.components.internal_search.base.schemas import (
    InternalSearchResult,
    InternalSearchState,
)
from unique_toolkit.components.internal_search.knowledge_base.schemas import (
    KnowledgeBaseInternalSearchState,
)
from unique_toolkit.content.schemas import ContentChunk

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


def _base_settings() -> UniqueSettings:
    return UniqueSettings(
        auth=AuthContext(
            user_id=SecretStr("user-1"),
            company_id=SecretStr("company-1"),
        ),
        app=UniqueApp(),
        api=UniqueApi(),
    )


@pytest.mark.ai
def test_chat_provider__build_service_binds_settings_with_placeholders():
    provider = ChatInternalSearchToolProvider(
        config=ChatInternalSearchMcpConfig(),
        context_provider=MagicMock(),
    )
    request_meta = InternalSearchRequestMeta.from_request_meta(
        {"unique.app/chat-id": "chat-1"}
    )
    fake_service = MagicMock()
    fake_service.bind_settings.return_value = fake_service

    with patch(
        "unique_mcp.internal_search.provider.ChatInternalSearchService.from_config",
        return_value=fake_service,
    ):
        service = provider._build_service(
            settings=_base_settings(),
            request_meta=request_meta,
        )

    bind_settings = fake_service.bind_settings.call_args.args[0]
    assert service is fake_service
    assert bind_settings.context.chat is not None
    assert bind_settings.context.chat.chat_id == "chat-1"
    assert bind_settings.context.chat.assistant_id == "mcp-internal-search"


@pytest.mark.ai
def test_chat_provider__populate_state_sets_content_ids():
    service = SimpleNamespace(state=InternalSearchState(search_queries=[]))
    request_meta = InternalSearchRequestMeta.from_request_meta(
        {
            "unique.app/selected-uploaded-file-ids": ["file-1", "file-2"],
            "unique.app/language-model-max-input-tokens": 128000,
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
            "unique.app/content-ids": ["doc-1"],
            "unique.app/metadata-filter": {"kind": "policy"},
        }
    )

    service.state.search_queries = ["policy"]
    service.state.content_ids = request_meta.knowledge_base_content_ids
    service.state.metadata_filter_override = request_meta.metadata_filter

    assert service.state.search_queries == ["policy"]
    assert service.state.content_ids == ["doc-1"]
    assert service.state.metadata_filter_override == {"kind": "policy"}


@pytest.mark.ai
def test_kb_provider__build_service_binds_settings():
    provider = KnowledgeBaseInternalSearchToolProvider(
        config=KnowledgeBaseInternalSearchMcpConfig(),
        context_provider=MagicMock(),
    )
    fake_service = MagicMock()
    fake_service.bind_settings.return_value = fake_service

    with patch(
        "unique_mcp.internal_search.provider.KnowledgeBaseInternalSearchService.from_config",
        return_value=fake_service,
    ):
        service = provider._build_service(settings=_base_settings())

    fake_service.bind_settings.assert_called_once()
    assert service is fake_service


@pytest.mark.ai
def test_provider__format_result_returns_chunk_text_and_meta():
    chunk = ContentChunk(chunk_id="c1", text="chunk text", start_page=1, end_page=1)
    result = _format_tool_result(
        config=KnowledgeBaseInternalSearchMcpConfig(),
        result=InternalSearchResult(
            chunks=[chunk],
            debug_info={"searchStrings": ["chunk"]},
        ),
    )

    assert isinstance(result.content[0], TextContent)
    assert result.content[0].text == "chunk text"
    assert result.content[0].meta["chunk"]["chunk_id"] == "c1"
