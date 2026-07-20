"""Tests for the MCP Apps chat window resource and legacy MCP-UI resource."""

import pytest
from fastmcp import Client, FastMCP
from mcp_space_chat.settings import McpSpaceChatSettings
from mcp_space_chat.server import (
    register_chat_window_resource,
    register_hello_world_resource,
)
from mcp_space_chat.ui_resource import (
    CHAT_WINDOW_URI,
    HELLO_WORLD_HEIGHT_PX,
    HELLO_WORLD_URI,
    HELLO_WORLD_WIDTH_PX,
    build_legacy_hello_world_resource,
    build_legacy_ui_resource,
    load_chat_window_html,
    load_hello_world_html,
)

pytestmark = pytest.mark.ai


def _chat_settings() -> McpSpaceChatSettings:
    return McpSpaceChatSettings(frontend_base_url="https://next.qa.unique.app")  # type: ignore[arg-type]


# ── Wrapper HTML ──────────────────────────────────────────────────────────────


def test_chat_window_html_is_a_full_document():
    html = load_chat_window_html()
    assert html.lstrip().startswith("<!DOCTYPE html>")


def test_chat_window_html_implements_mcp_apps_handshake():
    html = load_chat_window_html()
    assert "ui/initialize" in html
    assert "ui/notifications/initialized" in html
    assert "ui/notifications/tool-result" in html
    assert "ui/notifications/size-changed" in html
    assert "ui/resource-teardown" in html
    assert "ui/open-link" in html


def test_chat_window_html_reads_embed_url_from_structured_content():
    html = load_chat_window_html()
    assert "structuredContent" in html
    assert "embedUrl" in html


def test_hello_world_html_requests_preferred_size():
    html = load_hello_world_html()
    assert "Hello World" in html
    assert "ui/initialize" in html
    assert "ui/notifications/size-changed" in html
    assert str(HELLO_WORLD_WIDTH_PX) in html
    assert str(HELLO_WORLD_HEIGHT_PX) in html
    assert "animation" in html


# ── Settings ──────────────────────────────────────────────────────────────────


def test_frontend_origin_strips_path_and_default_port():
    settings = _chat_settings()
    assert settings.frontend_origin() == "https://next.qa.unique.app"


def test_frontend_origin_keeps_custom_port():
    settings = McpSpaceChatSettings(frontend_base_url="http://localhost:3000")  # type: ignore[arg-type]
    assert settings.frontend_origin() == "http://localhost:3000"


# ── Resource registration (MCP Apps) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_chat_window_resource_declares_mcp_app_mime_and_frame_csp():
    mcp = FastMCP("test")
    register_chat_window_resource(mcp, _chat_settings())

    async with Client(mcp) as client:
        resources = await client.list_resources()
        resource = next(r for r in resources if str(r.uri) == CHAT_WINDOW_URI)
        assert resource.mimeType == "text/html;profile=mcp-app"
        assert resource.meta is not None
        assert resource.meta["ui"]["csp"]["frameDomains"] == [
            "https://next.qa.unique.app"
        ]

        contents = await client.read_resource(CHAT_WINDOW_URI)
        assert contents[0].mimeType == "text/html;profile=mcp-app"
        assert "ui/initialize" in contents[0].text  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_hello_world_resource_is_mcp_app_html():
    mcp = FastMCP("test")
    register_hello_world_resource(mcp)

    async with Client(mcp) as client:
        resources = await client.list_resources()
        resource = next(r for r in resources if str(r.uri) == HELLO_WORLD_URI)
        assert resource.mimeType == "text/html;profile=mcp-app"

        contents = await client.read_resource(HELLO_WORLD_URI)
        assert "Hello World" in contents[0].text  # type: ignore[union-attr]
        assert "size-changed" in contents[0].text  # type: ignore[union-attr]


# ── Legacy MCP-UI resource ────────────────────────────────────────────────────


def test_legacy_ui_resource_is_external_url_embed():
    embed_url = "https://next.qa.unique.app/chat/embed/chat_1?spaceId=assistant_a"
    resource = build_legacy_ui_resource(embed_url, "chat_1")

    assert resource.type == "resource"
    assert str(resource.resource.uri) == "ui://space-chat/embed/chat_1"
    assert resource.resource.mimeType == "text/uri-list"
    assert resource.resource.text == embed_url  # type: ignore[union-attr]


def test_legacy_hello_world_resource_is_raw_html_with_preferred_size():
    resource = build_legacy_hello_world_resource()

    assert resource.type == "resource"
    assert resource.resource.mimeType == "text/html"
    assert "Hello World" in resource.resource.text  # type: ignore[union-attr]
    assert resource.resource.meta == {
        "mcpui.dev/ui-preferred-frame-size": [
            f"{HELLO_WORLD_WIDTH_PX}px",
            f"{HELLO_WORLD_HEIGHT_PX}px",
        ]
    }
