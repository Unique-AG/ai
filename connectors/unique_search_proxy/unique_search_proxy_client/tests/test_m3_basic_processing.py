from __future__ import annotations

import pytest
from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles
from unique_search_proxy_core.crawlers.basic.processing.policy import (
    ContentTypeHandlerPolicy,
)
from unique_search_proxy_core.crawlers.basic.schema import BasicConfig

from unique_search_proxy_client.web.core.crawlers.basic.processing import (
    CONTENT_TYPE_PROCESSORS,
    ContentProcessingError,
    process_content,
    resolve_handler_policy,
    resolve_processor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.html_markdown import (
    html_to_markdown,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.html import (
    process_html,
)


@pytest.mark.ai
def test_processing_map_includes_html_and_pdf() -> None:
    assert CONTENT_TYPE_PROCESSORS["text/html"] is process_html
    assert "application/pdf" in CONTENT_TYPE_PROCESSORS


@pytest.mark.ai
def test_resolve_processor_returns_none_for_unknown_type() -> None:
    assert resolve_processor("application/octet-stream") is None


@pytest.mark.ai
def test_resolve_handler_policy() -> None:
    handlers = {
        "text/html": ContentTypeHandlerPolicy.ALLOW,
        "application/pdf": ContentTypeHandlerPolicy.FORBID,
    }
    assert (
        resolve_handler_policy("text/html", handlers) is ContentTypeHandlerPolicy.ALLOW
    )
    assert (
        resolve_handler_policy("application/pdf", handlers)
        is ContentTypeHandlerPolicy.FORBID
    )
    assert resolve_handler_policy("image/png", handlers) is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_process_content_html_when_allowed() -> None:
    html = "<h1>Title</h1><p>Body</p>"
    handlers = {"text/html": ContentTypeHandlerPolicy.ALLOW}
    content = await process_content(html, "text/html", handlers=handlers, timeout=10.0)
    assert content is not None
    assert "Title" in content
    assert "Body" in content


@pytest.mark.ai
@pytest.mark.asyncio
async def test_process_content_skips_forbidden_type() -> None:
    handlers = {"text/html": ContentTypeHandlerPolicy.FORBID}
    assert (
        await process_content(
            "<p>x</p>",
            "text/html",
            handlers=handlers,
            timeout=10.0,
        )
        is None
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_process_content_pdf_raises_when_allowed() -> None:
    handlers = {"application/pdf": ContentTypeHandlerPolicy.ALLOW}
    with pytest.raises(ContentProcessingError, match="PDF processing"):
        await process_content(
            "%PDF", "application/pdf", handlers=handlers, timeout=10.0
        )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_process_content_unlisted_type_returns_none() -> None:
    handlers = {"text/html": ContentTypeHandlerPolicy.ALLOW}
    assert (
        await process_content(
            "data",
            "application/octet-stream",
            handlers=handlers,
            timeout=10.0,
        )
        is None
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_process_content_allow_without_processor_raises() -> None:
    handlers = {"application/octet-stream": ContentTypeHandlerPolicy.ALLOW}
    with pytest.raises(ContentProcessingError, match="No processor registered"):
        await process_content(
            "data",
            "application/octet-stream",
            handlers=handlers,
            timeout=10.0,
        )


@pytest.mark.ai
def test_content_types_to_handlers() -> None:
    toggles = ContentTypeToggles(
        html=True,
        xhtml=False,
        plain_text=False,
        markdown=False,
        pdf=True,
    )
    assert toggles.to_handlers() == {
        "text/html": ContentTypeHandlerPolicy.ALLOW,
        "application/pdf": ContentTypeHandlerPolicy.ALLOW,
    }


@pytest.mark.ai
def test_content_types_defaults_enable_common_text_types() -> None:
    toggles = BasicConfig().content_types
    assert toggles == ContentTypeToggles()
    assert toggles.to_handlers() == {
        "text/html": ContentTypeHandlerPolicy.ALLOW,
        "application/xhtml+xml": ContentTypeHandlerPolicy.ALLOW,
        "text/plain": ContentTypeHandlerPolicy.ALLOW,
        "text/markdown": ContentTypeHandlerPolicy.ALLOW,
    }


@pytest.mark.ai
def test_html_to_markdown_converts_headings() -> None:
    markdown = html_to_markdown("<h1>Title</h1><p>Body</p>")
    assert "Title" in markdown
    assert "Body" in markdown
