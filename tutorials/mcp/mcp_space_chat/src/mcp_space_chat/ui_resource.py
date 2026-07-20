"""UI resources for the space chat window.

Two rendering paths are supported:

- **MCP Apps hosts** (Claude, VS Code Copilot, ...): tools carry
  ``_meta.ui.resourceUri`` pointing at :data:`CHAT_WINDOW_URI`. The host reads
  that resource (``text/html;profile=mcp-app``), renders it in a sandboxed
  iframe, and the wrapper HTML mounts a nested iframe with the real Unique
  chat embed. The frontend origin must be declared via ``csp.frameDomains``.

- **Legacy MCP-UI hosts** (Goose, Postman, MCPJam, ...): the tool result also
  embeds a classic MCP-UI ``externalUrl`` resource pointing straight at the
  embed URL; these hosts iframe it directly.
"""

from __future__ import annotations

from pathlib import Path

from mcp.types import EmbeddedResource
from mcp_ui_server import create_ui_resource

CHAT_WINDOW_URI = "ui://space-chat/chat-window"
HELLO_WORLD_URI = "ui://space-chat/hello-world"

# Preferred viewport for the hello-world smoke-test app (MCP Apps size-changed).
HELLO_WORLD_WIDTH_PX = 560
HELLO_WORLD_HEIGHT_PX = 360

# Preferred viewport for the native chat panel fallback.
CHAT_WINDOW_WIDTH_PX = 760
CHAT_WINDOW_HEIGHT_PX = 600

_UI_DIR = Path(__file__).parent / "ui"
_CHAT_WINDOW_HTML_PATH = _UI_DIR / "chat_window.html"
_HELLO_WORLD_HTML_PATH = _UI_DIR / "hello_world.html"
_VENDOR_MARKED_PATH = _UI_DIR / "vendor" / "marked.min.js"
_VENDOR_PURIFY_PATH = _UI_DIR / "vendor" / "purify.min.js"

# Placeholder in chat_window.html replaced with inlined vendor scripts so the
# sandboxed MCP Apps iframe never needs to fetch a CDN (CSP-safe).
_VENDOR_SCRIPTS_PLACEHOLDER = "<!-- VENDOR_SCRIPTS -->"


def _vendor_scripts_html() -> str:
    """Return <script> tags containing marked.js and DOMPurify."""
    marked = _VENDOR_MARKED_PATH.read_text(encoding="utf-8")
    purify = _VENDOR_PURIFY_PATH.read_text(encoding="utf-8")
    return (
        f"<script>\n{marked}\n</script>\n"
        f"<script>\n{purify}\n</script>\n"
    )


def load_chat_window_html() -> str:
    """Return the MCP Apps wrapper HTML for the chat window.

    Inlines vendored marked.js + DOMPurify so the panel can render markdown
    without external network access inside the host sandbox.
    """
    html = _CHAT_WINDOW_HTML_PATH.read_text(encoding="utf-8")
    if _VENDOR_SCRIPTS_PLACEHOLDER not in html:
        return html
    return html.replace(_VENDOR_SCRIPTS_PLACEHOLDER, _vendor_scripts_html())


def load_hello_world_html() -> str:
    """Return the MCP Apps Hello World smoke-test HTML."""
    return _HELLO_WORLD_HTML_PATH.read_text(encoding="utf-8")


def build_legacy_hello_world_resource() -> EmbeddedResource:
    """Build a legacy MCP-UI ``rawHtml`` resource for hosts without MCP Apps."""
    return create_ui_resource(
        {
            "uri": "ui://space-chat/hello-world-legacy",
            "content": {"type": "rawHtml", "htmlString": load_hello_world_html()},
            "encoding": "text",
            "uiMetadata": {
                "preferred-frame-size": [
                    f"{HELLO_WORLD_WIDTH_PX}px",
                    f"{HELLO_WORLD_HEIGHT_PX}px",
                ],
            },
        }
    )


def build_legacy_ui_resource(embed_url: str, chat_id: str) -> EmbeddedResource:
    """Build a legacy MCP-UI ``externalUrl`` resource for ``embed_url``.

    MCP-UI hosts render this embedded resource as an iframe with
    ``src=embed_url`` — the same chat window the browser extension shows.
    ``UIResource`` subclasses :class:`mcp.types.EmbeddedResource`, so it can
    be used directly as a tool-result content block.
    """
    return create_ui_resource(
        {
            "uri": f"ui://space-chat/embed/{chat_id}",
            "content": {"type": "externalUrl", "iframeUrl": embed_url},
            "encoding": "text",
            "uiMetadata": {
                "preferred-frame-size": ["100%", "640px"],
                "initial-render-data": {"chatId": chat_id},
            },
        }
    )
