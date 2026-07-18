"""Tests for the search tool — config schema, routing logic, and references."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import CallToolResult
from mcp_search.config import SearchToolConfig
from mcp_search.references import (
    REFERENCE_META_KEY,
    chunk_to_text_content,
    reference_url,
)
from mcp_search.tools.search import search

from unique_mcp.meta.rjsf import ConfigSchemaMeta
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.experimental.components.internal_search import (
    KnowledgeBaseInternalSearchConfig,
)

# ── Schema tests ──────────────────────────────────────────────────────────────


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


# ── Routing tests ─────────────────────────────────────────────────────────────


def _make_chunk(text: str, **kwargs) -> ContentChunk:
    return ContentChunk(
        id=kwargs.pop("id", "cont_abcdefgehijklmnopqrstuvwx"),
        text=text,
        order=0,
        **kwargs,
    )


def _make_settings():
    return MagicMock()


def _patch_post_processor(chunks: list):
    """Patch InternalSearchPostProcessor so process() returns the given chunks."""
    mock_pp = MagicMock()
    mock_pp.process = AsyncMock(return_value=chunks)
    return patch(
        "mcp_search.tools.search.InternalSearchPostProcessor.from_settings",
        return_value=mock_pp,
    )


def _patch_resolve_settings():
    """Keep injected settings as-is (identity resolution covered in test_auth)."""
    return patch(
        "mcp_search.tools.search.resolve_search_settings",
        new=AsyncMock(side_effect=lambda s: s),
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
        _patch_resolve_settings(),
    ):
        result = await search(
            search_string="test query",
            config=SearchToolConfig(),
            settings=_make_settings(),
        )

    mock_from_config.assert_called_once_with(SearchToolConfig().service_config)
    mock_service.bind_settings.assert_called_once()
    assert mock_service.state.search_queries == ["test query"]
    assert isinstance(result, CallToolResult)
    assert len(result.content) == 1


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
        _patch_resolve_settings(),
    ):
        result = await search(
            search_string="fallback query",
            config=SearchToolConfig(),
            settings=_make_settings(),
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
        _patch_resolve_settings(),
    ):
        result = await search(
            search_string="query",
            config=SearchToolConfig(),
            settings=_make_settings(),
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
        _patch_resolve_settings(),
    ):
        result = await search(
            search_string="query",
            config=SearchToolConfig(),
            settings=_make_settings(),
        )

    assert result.isError is True
    assert "post-processor failed" in result.content[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_search_returns_error_when_identity_unresolvable():
    with patch(
        "mcp_search.tools.search.resolve_search_settings",
        new=AsyncMock(side_effect=ValueError("Refusing to fall back to UNIQUE_AUTH_")),
    ):
        result = await search(
            search_string="query",
            config=SearchToolConfig(),
            settings=_make_settings(),
        )

    assert result.isError is True
    assert "UNIQUE_AUTH_" in result.content[0].text  # type: ignore[union-attr]


# ── Reference tests ───────────────────────────────────────────────────────────


def test_reference_url_internal_content_uses_unique_scheme():
    chunk = _make_chunk("text")
    assert reference_url(chunk) == "unique://content/cont_abcdefgehijklmnopqrstuvwx"


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


def test_chunk_to_text_content_has_source_header_and_reference_meta():
    chunk = _make_chunk(
        "The revenue grew by 12%.",
        title="Annual Report 2025",
        chunk_id="chunk_abcdefgehijklmnopqrstuv",
        start_page=12,
        end_page=14,
    )

    content = chunk_to_text_content(chunk, sequence_number=3)

    assert content.text.startswith(
        "[source3] Annual Report 2025 (pages 12-14)\n"
        "unique://content/cont_abcdefgehijklmnopqrstuvwx\n"
    )
    assert content.text.endswith("The revenue grew by 12%.")

    assert content.meta is not None
    reference = content.meta[REFERENCE_META_KEY]
    assert reference["url"] == "unique://content/cont_abcdefgehijklmnopqrstuvwx"
    assert reference["sequenceNumber"] == 3
    assert reference["source"] == "node-ingestion-chunks"
    assert (
        reference["sourceId"]
        == "cont_abcdefgehijklmnopqrstuvwx_chunk_abcdefgehijklmnopqrstuv"
    )


@pytest.mark.asyncio
async def test_search_results_are_numbered_sequentially():
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
        _patch_resolve_settings(),
    ):
        result = await search(
            search_string="query",
            config=SearchToolConfig(),
            settings=_make_settings(),
        )

    assert [c.text.split("]")[0] for c in result.content] == [  # type: ignore[union-attr]
        "[source1",
        "[source2",
    ]
