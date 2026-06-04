from __future__ import annotations

from pydantic import BaseModel, Field

from unique_search_proxy_core.crawlers.basic.processing.policy import (
    ContentTypeHandlerPolicy,
)
from unique_search_proxy_core.schema import get_model_config

# Supported media types for the basic crawler (must match registered processors).
CONTENT_TYPE_TOGGLE_TO_MIME: dict[str, str] = {
    "html": "text/html",
    "xhtml": "application/xhtml+xml",
    "plain_text": "text/plain",
    "markdown": "text/markdown",
    "pdf": "application/pdf",
}


class ContentTypeToggles(BaseModel):
    """Per-type activation flags for basic-crawler content processing."""

    model_config = get_model_config(title="Content Types")

    html: bool = Field(default=True, title="HTML", description="text/html")
    xhtml: bool = Field(
        default=True,
        title="XHTML",
        description="application/xhtml+xml",
    )
    plain_text: bool = Field(default=True, title="Plain text", description="text/plain")
    markdown: bool = Field(default=True, title="Markdown", description="text/markdown")
    pdf: bool = Field(default=False, title="PDF", description="application/pdf")

    def to_handlers(self) -> dict[str, ContentTypeHandlerPolicy]:
        """Map enabled toggles to allow-policies for the processing registry."""
        return {
            mime_type: ContentTypeHandlerPolicy.ALLOW
            for field_name, mime_type in CONTENT_TYPE_TOGGLE_TO_MIME.items()
            if getattr(self, field_name)
        }


__all__ = [
    "CONTENT_TYPE_TOGGLE_TO_MIME",
    "ContentTypeToggles",
]
