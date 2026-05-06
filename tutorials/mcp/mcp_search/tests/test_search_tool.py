"""Tests for the search tool — config schema and routing logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import CallToolResult
from mcp_search.config import ChatSearchConfig, KBSearchConfig, SearchToolConfig
from mcp_search.tools.search import search

from unique_toolkit._common.pydantic.rjsf_tags import ui_schema_for_model
from unique_toolkit.content.schemas import ContentChunk

# ── Schema tests ──────────────────────────────────────────────────────────────


def test_json_schema_has_oneof_discriminator():
    schema = SearchToolConfig.model_json_schema()
    sc = schema["properties"]["serviceConfig"]
    assert "oneOf" in sc
    assert sc["discriminator"]["propertyName"] == "type"
    assert sc["discriminator"]["mapping"] == {
        "kb": "#/$defs/KBSearchConfig",
        "chat": "#/$defs/ChatSearchConfig",
    }


def test_json_schema_kb_variant_has_metadata_filter():
    schema = SearchToolConfig.model_json_schema()
    kb = schema["$defs"]["KBSearchConfig"]["properties"]
    assert "metadataFilter" in kb
    assert "type" in kb
    assert kb["type"]["const"] == "kb"


def test_json_schema_chat_variant_has_no_metadata_filter():
    schema = SearchToolConfig.model_json_schema()
    chat = schema["$defs"]["ChatSearchConfig"]["properties"]
    assert "metadataFilter" not in chat
    assert chat["type"]["const"] == "chat"


def test_ui_schema_hides_max_tokens_for_sources():
    ui = ui_schema_for_model(SearchToolConfig)
    assert ui["post_processing"]["max_tokens_for_sources"] == {"ui:widget": "hidden"}


def test_default_config_is_kb_and_round_trips():
    default = SearchToolConfig().model_dump(mode="json")
    assert default["service_config"]["type"] == "kb"
    # Round-trip: stored config must validate back without error
    restored = SearchToolConfig.model_validate(default)
    assert isinstance(restored.service_config, KBSearchConfig)


def test_validate_chat_config():
    config = SearchToolConfig.model_validate({"service_config": {"type": "chat"}})
    assert isinstance(config.service_config, ChatSearchConfig)


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
async def test_search_routes_to_kb_service():
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
            config=SearchToolConfig(),  # type=kb by default
            settings=_make_settings(),
        )

    mock_from_config.assert_called_once()
    assert isinstance(mock_from_config.call_args[0][0], KBSearchConfig)
    mock_service.bind_settings.assert_called_once()
    assert mock_service.state.search_queries == ["test query"]
    assert isinstance(result, CallToolResult)
    assert len(result.content) == 1


@pytest.mark.asyncio
async def test_search_routes_to_chat_service():
    chunks = [_make_chunk("chat result")]
    mock_service = MagicMock()
    mock_service.bind_settings.return_value = mock_service
    mock_service.state = MagicMock()
    mock_service.run = AsyncMock(return_value=MagicMock())

    config = SearchToolConfig.model_validate({"service_config": {"type": "chat"}})

    with (
        patch(
            "mcp_search.tools.search.ChatInternalSearchService.from_config",
            return_value=mock_service,
        ) as mock_from_config,
        _patch_post_processor(chunks),
    ):
        result = await search(
            search_string="chat query",
            config=config,
            settings=_make_settings(),
        )

    mock_from_config.assert_called_once()
    assert isinstance(mock_from_config.call_args[0][0], ChatSearchConfig)
    assert mock_service.state.search_queries == ["chat query"]
    assert isinstance(result, CallToolResult)


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
            config=SearchToolConfig(),  # explicit defaults
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
