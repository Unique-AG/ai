"""Tests for the search tool — config schema, routing logic, and references."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import CallToolResult
from mcp_search.config import SearchToolConfig
from mcp_search.references import (
    CITATION_RESULT_INSTRUCTION,
    REFERENCE_FORMAT_INFORMATION,
    REFERENCE_META_KEY,
    chunk_to_text_content,
    frontend_document_url,
    markdown_citation_link,
    reference_url,
    scope_id_from_folder_id_path,
)
from mcp_search.tools.search import _TOOL_DESCRIPTION, search

from unique_mcp.meta.rjsf import ConfigSchemaMeta
from unique_toolkit.content.schemas import ContentChunk, ContentMetadata
from unique_toolkit.experimental.components.internal_search import (
    KnowledgeBaseInternalSearchConfig,
)


def test_json_schema_has_service_config():
    schema = SearchToolConfig.model_json_schema()
    assert "serviceConfig" in schema["properties"]


def test_json_schema_service_config_has_metadata_filter():
    schema = SearchToolConfig.model_json_schema()
    sc_ref = schema["properties"]["serviceConfig"].get("$ref", "")
    def_name = sc_ref.split("/")[-1]
    kb_props = schema["$defs"][def_name]["properties"]
    assert "metadataFilter" in kb_props


def test_ui_schema_hides_max_tokens_for_sources():
    meta: dict = {}
    ConfigSchemaMeta(SearchToolConfig).merge_into_meta(meta)
    ui = meta["unique.app/config-schema"]["ui_schema"]
    assert ui["postProcessing"]["maxTokensForSources"] == {"ui:widget": "hidden"}


def test_default_config_round_trips():
    default = SearchToolConfig().model_dump(mode="json")
    restored = SearchToolConfig.model_validate(default)
    assert isinstance(restored.service_config, KnowledgeBaseInternalSearchConfig)


def test_tool_description_includes_citation_rules():
    assert "Do NOT invent placeholders like [source1]" in _TOOL_DESCRIPTION
    assert REFERENCE_FORMAT_INFORMATION in _TOOL_DESCRIPTION


def _make_chunk(text: str, **kwargs) -> ContentChunk:
    return ContentChunk(
        id=kwargs.pop("id", "cont_abcdefgehijklmnopqrstuvwx"),
        text=text,
        order=0,
        **kwargs,
    )


def _patch_post_processor(chunks: list):
    """Patch InternalSearchPostProcessor so process() returns the given chunks."""
    mock_pp = MagicMock()
    mock_pp.process = AsyncMock(return_value=chunks)
    return patch(
        "mcp_search.tools.search.InternalSearchPostProcessor.from_settings",
        return_value=mock_pp,
    )


def _patch_identity():
    """Per-request identity resolves in-body via unique_mcp; return a stub."""
    return patch(
        "mcp_search.tools.search.get_unique_settings_async",
        new=AsyncMock(return_value=MagicMock()),
    )


def _patch_frontend_settings(base_url: str | None = None):
    mock_settings = MagicMock()
    mock_settings.frontend_base_url_str.return_value = base_url
    return patch(
        "mcp_search.tools.search.McpSearchServerSettings",
        return_value=mock_settings,
    )


def _patch_resolve_scope_ids(mapping: dict[str, str] | None = None):
    return patch(
        "mcp_search.tools.search.resolve_scope_ids",
        new=AsyncMock(return_value=mapping or {}),
    )


@pytest.mark.asyncio
async def test_search_calls_kb_service():
    chunks = [_make_chunk("result A")]
    mock_service = MagicMock()
    mock_service.bind_settings.return_value = mock_service
    mock_service.state = MagicMock()
    mock_service.run = AsyncMock(return_value=MagicMock())

    with (
        patch(
            "mcp_search.tools.search.KnowledgeBaseInternalSearchService.from_config",
            return_value=mock_service,
        ) as mock_from_config,
        _patch_post_processor(chunks),
        _patch_identity(),
        _patch_frontend_settings(None),
        _patch_resolve_scope_ids(),
    ):
        result = await search(
            search_string="test query",
            config=SearchToolConfig(),
        )

    mock_from_config.assert_called_once_with(SearchToolConfig().service_config)
    mock_service.bind_settings.assert_called_once()
    assert mock_service.state.search_queries == ["test query"]
    assert isinstance(result, CallToolResult)
    # result chunks + trailing citation instruction
    assert len(result.content) == 2


@pytest.mark.asyncio
async def test_search_uses_defaults_when_no_config_provided():
    chunks = [_make_chunk("default")]
    mock_service = MagicMock()
    mock_service.bind_settings.return_value = mock_service
    mock_service.state = MagicMock()
    mock_service.run = AsyncMock(return_value=MagicMock())

    with (
        patch(
            "mcp_search.tools.search.KnowledgeBaseInternalSearchService.from_config",
            return_value=mock_service,
        ),
        _patch_post_processor(chunks),
        _patch_identity(),
        _patch_frontend_settings(None),
        _patch_resolve_scope_ids(),
    ):
        result = await search(
            search_string="fallback query",
            config=SearchToolConfig(),
        )

    assert isinstance(result, CallToolResult)
    assert mock_service.state.search_queries == ["fallback query"]


@pytest.mark.asyncio
async def test_search_returns_error_result_on_service_failure():
    with (
        patch(
            "mcp_search.tools.search.KnowledgeBaseInternalSearchService.from_config",
            side_effect=RuntimeError("KB unavailable"),
        ),
        _patch_identity(),
    ):
        result = await search(
            search_string="query",
            config=SearchToolConfig(),
        )

    assert result.isError is True
    assert "KB unavailable" in result.content[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_search_returns_error_result_on_post_processor_failure():
    mock_service = MagicMock()
    mock_service.bind_settings.return_value = mock_service
    mock_service.state = MagicMock()
    mock_service.run = AsyncMock(return_value=MagicMock())

    mock_pp = MagicMock()
    mock_pp.process = AsyncMock(side_effect=RuntimeError("post-processor failed"))

    with (
        patch(
            "mcp_search.tools.search.KnowledgeBaseInternalSearchService.from_config",
            return_value=mock_service,
        ),
        patch(
            "mcp_search.tools.search.InternalSearchPostProcessor.from_settings",
            return_value=mock_pp,
        ),
        _patch_identity(),
    ):
        result = await search(
            search_string="query",
            config=SearchToolConfig(),
        )

    assert result.isError is True
    assert "post-processor failed" in result.content[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_search_returns_error_when_identity_unresolvable():
    with patch(
        "mcp_search.tools.search.get_unique_settings_async",
        new=AsyncMock(side_effect=ValueError("Refusing to fall back to UNIQUE_AUTH_")),
    ):
        result = await search(
            search_string="query",
            config=SearchToolConfig(),
        )

    assert result.isError is True
    assert "UNIQUE_AUTH_" in result.content[0].text  # type: ignore[union-attr]


def test_scope_id_from_folder_id_path_takes_leaf():
    assert scope_id_from_folder_id_path("uniquepathid://scope_a/scope_b") == "scope_b"


def test_frontend_document_url_shape():
    url = frontend_document_url(
        "https://example.unique.app",
        "scope_uy3cznkuysy3gasrxx2m4ezb",
        "cont_mvkp2iv25xy4cxccpq6i6byk",
    )
    assert url == (
        "https://example.unique.app/knowledge-upload/"
        "scope_uy3cznkuysy3gasrxx2m4ezb?file=cont_mvkp2iv25xy4cxccpq6i6byk"
    )


def test_reference_url_internal_content_uses_unique_scheme():
    chunk = _make_chunk("text")
    assert reference_url(chunk) == "unique://content/cont_abcdefgehijklmnopqrstuvwx"


def test_reference_url_builds_frontend_deep_link_when_configured():
    chunk = _make_chunk(
        "text",
        metadata=ContentMetadata(
            key="doc.pdf",
            mime_type="application/pdf",
            folderIdPath="uniquepathid://scope_root/scope_leaf",  # type: ignore[call-arg]
        ),
    )
    assert reference_url(chunk, frontend_base_url="https://example.unique.app") == (
        "https://example.unique.app/knowledge-upload/scope_leaf"
        "?file=cont_abcdefgehijklmnopqrstuvwx"
    )


def test_reference_url_internally_stored_web_chunk_uses_unique_scheme():
    chunk = _make_chunk(
        "text",
        url="https://example.com/doc",
        internally_stored_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert reference_url(chunk) == "unique://content/cont_abcdefgehijklmnopqrstuvwx"


def test_reference_url_external_chunk_keeps_original_url():
    chunk = _make_chunk("text", url="https://example.com/doc")
    assert reference_url(chunk) == "https://example.com/doc"


def test_markdown_citation_link_escapes_sm_folder_path():
    """Primary Fix 3 fixture matching the Unique AI stringified paste."""
    path = "[" + "SM" + "]/AlpenSys/Audit_Report_AlpenSys_FY2023.pdf"
    link = markdown_citation_link(
        path, "unique://content/cont_ioi3voailf7hr011zcp6b7eh"
    )
    assert link == (
        "[\\[SM\\]/AlpenSys/Audit_Report_AlpenSys_FY2023.pdf]"
        "(unique://content/cont_ioi3voailf7hr011zcp6b7eh)"
    )
    assert not link.startswith("[[")


def test_chunk_to_text_content_escapes_brackets_in_title():
    title = "[" + "SM" + "]/AlpenSys/notes.txt"
    chunk = _make_chunk(
        "body",
        title=title,
        chunk_id="chunk_abcdefgehijklmnopqrstuv",
    )
    content = chunk_to_text_content(chunk, sequence_number=1)
    assert content.text.startswith(
        "[\\[SM\\]/AlpenSys/notes.txt]"
        "(unique://content/cont_abcdefgehijklmnopqrstuvwx)\n"
    )


def test_chunk_to_text_content_has_markdown_link_header_and_reference_meta():
    chunk = _make_chunk(
        "The revenue grew by 12%.",
        title="Annual Report 2025",
        chunk_id="chunk_abcdefgehijklmnopqrstuv",
        start_page=12,
        end_page=14,
    )

    content = chunk_to_text_content(chunk, sequence_number=3)

    assert content.text.startswith(
        "[Annual Report 2025](unique://content/cont_abcdefgehijklmnopqrstuvwx)"
        " (pages 12-14)\n"
    )
    assert content.text.endswith("The revenue grew by 12%.")
    assert "[source" not in content.text

    assert content.meta is not None
    reference = content.meta[REFERENCE_META_KEY]
    assert reference["url"] == "unique://content/cont_abcdefgehijklmnopqrstuvwx"
    assert reference["sequenceNumber"] == 3
    assert reference["source"] == "node-ingestion-chunks"
    assert (
        reference["sourceId"]
        == "cont_abcdefgehijklmnopqrstuvwx_chunk_abcdefgehijklmnopqrstuv"
    )


def test_chunk_to_text_content_uses_frontend_url_in_text_but_unique_in_meta():
    chunk = _make_chunk(
        "body",
        title="CV.pdf",
        id="cont_mvkp2iv25xy4cxccpq6i6byk",
    )
    content = chunk_to_text_content(
        chunk,
        sequence_number=1,
        frontend_base_url="https://example.unique.app",
        scope_id="scope_uy3cznkuysy3gasrxx2m4ezb",
    )
    assert (
        "https://example.unique.app/knowledge-upload/"
        "scope_uy3cznkuysy3gasrxx2m4ezb?file=cont_mvkp2iv25xy4cxccpq6i6byk"
    ) in content.text
    assert content.meta is not None
    assert (
        content.meta[REFERENCE_META_KEY]["url"]
        == "unique://content/cont_mvkp2iv25xy4cxccpq6i6byk"
    )


@pytest.mark.asyncio
async def test_search_results_are_numbered_sequentially_and_include_citation_block():
    chunks = [_make_chunk("first"), _make_chunk("second")]
    mock_service = MagicMock()
    mock_service.bind_settings.return_value = mock_service
    mock_service.state = MagicMock()
    mock_service.run = AsyncMock(return_value=MagicMock())

    with (
        patch(
            "mcp_search.tools.search.KnowledgeBaseInternalSearchService.from_config",
            return_value=mock_service,
        ),
        _patch_post_processor(chunks),
        _patch_identity(),
        _patch_frontend_settings(None),
        _patch_resolve_scope_ids(),
    ):
        result = await search(
            search_string="query",
            config=SearchToolConfig(),
        )

    texts = [c.text for c in result.content]  # type: ignore[union-attr]
    assert texts[0].startswith("[")
    assert "](unique://content/" in texts[0]
    assert "](unique://content/" in texts[1]
    assert "[source" not in texts[0]
    assert texts[2] == CITATION_RESULT_INSTRUCTION


@pytest.mark.asyncio
async def test_search_uses_frontend_deep_links_when_scopes_resolved():
    chunks = [
        _make_chunk("first", id="cont_aaaaaaaaaaaaaaaaaaaaaaa1", title="A.pdf"),
    ]
    mock_service = MagicMock()
    mock_service.bind_settings.return_value = mock_service
    mock_service.state = MagicMock()
    mock_service.run = AsyncMock(return_value=MagicMock())

    with (
        patch(
            "mcp_search.tools.search.KnowledgeBaseInternalSearchService.from_config",
            return_value=mock_service,
        ),
        _patch_post_processor(chunks),
        _patch_identity(),
        _patch_frontend_settings("https://example.unique.app"),
        _patch_resolve_scope_ids(
            {"cont_aaaaaaaaaaaaaaaaaaaaaaa1": "scope_uy3cznkuysy3gasrxx2m4ezb"}
        ),
    ):
        result = await search(
            search_string="query",
            config=SearchToolConfig(),
        )

    assert (
        "https://example.unique.app/knowledge-upload/"
        "scope_uy3cznkuysy3gasrxx2m4ezb?file=cont_aaaaaaaaaaaaaaaaaaaaaaa1"
    ) in result.content[0].text  # type: ignore[union-attr]
