"""Tests for the search tool — config schema and routing logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import CallToolResult
from mcp_search.config import SearchToolConfig
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


def _make_chunk(text: str) -> ContentChunk:
    return MagicMock(
        spec=ContentChunk, text=text, model_dump=MagicMock(return_value={})
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
    with patch(
        "mcp_search.tools.search.KnowledgeBaseInternalSearchService.from_config",
        side_effect=RuntimeError("KB unavailable"),
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
    ):
        result = await search(
            search_string="query",
            config=SearchToolConfig(),
            settings=_make_settings(),
        )

    assert result.isError is True
    assert "post-processor failed" in result.content[0].text  # type: ignore[union-attr]
