from __future__ import annotations

import asyncio
import threading
import time

import pytest
from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles
from unique_search_proxy_core.crawlers.basic.processing.policy import (
    ContentTypeHandlerPolicy,
)
from unique_search_proxy_core.crawlers.basic.schema import BasicConfig

from unique_search_proxy_client.web.core.crawlers.basic.processing import (
    CONTENT_TYPE_PROCESSORS,
    ContentProcessingError,
    html_markdown,
    process_content,
    resolve_handler_policy,
    resolve_processor,
)
from unique_search_proxy_client.web.core.crawlers.basic.processing.html_markdown import (
    CONVERSION_THREADS,
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


@pytest.mark.ai
@pytest.mark.asyncio
async def test_html_to_markdown_async__runs_on_bounded_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify concurrent conversions share a pool of CONVERSION_THREADS threads.
    Why this matters: Each running conversion holds a parsed page in memory, and
        the default executor would run up to 16 at once per worker.
    Setup summary: Record the thread of each conversion, run 8 at once, assert
        results come back in order from at most CONVERSION_THREADS pool threads.
    """
    thread_names: set[str] = set()

    def record_thread(html: str) -> str:
        thread_names.add(threading.current_thread().name)
        time.sleep(0.01)
        return html

    monkeypatch.setattr(html_markdown, "html_to_markdown", record_thread)

    pages = [f"<p>{index}</p>" for index in range(8)]
    results = await asyncio.gather(
        *(html_markdown.html_to_markdown_async(page, timeout=10) for page in pages)
    )

    assert results == pages
    assert 1 <= len(thread_names) <= CONVERSION_THREADS
    assert all(name.startswith("html-to-markdown") for name in thread_names)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_html_to_markdown_async__drops_queued_conversion_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify a conversion that times out while queued never runs.
    Why this matters: Work for a request that already failed must not hold
        memory or CPU afterwards.
    Setup summary: Block every pool thread, time out a queued conversion, then
        release the pool and run one more; assert the timed-out page never started.
    """
    release = threading.Event()
    started: list[str] = []

    def block_until_released(html: str) -> str:
        started.append(html)
        release.wait(timeout=5)
        return html

    monkeypatch.setattr(html_markdown, "html_to_markdown", block_until_released)

    busy = [
        asyncio.ensure_future(
            html_markdown.html_to_markdown_async(f"busy-{i}", timeout=10)
        )
        for i in range(CONVERSION_THREADS)
    ]
    try:
        deadline = time.monotonic() + 5
        while len(started) < CONVERSION_THREADS and time.monotonic() < deadline:
            await asyncio.sleep(0.01)
        assert len(started) == CONVERSION_THREADS

        with pytest.raises(TimeoutError):
            await html_markdown.html_to_markdown_async("queued", timeout=0.05)
    finally:
        release.set()
        await asyncio.gather(*busy)

    assert await html_markdown.html_to_markdown_async("after", timeout=10) == "after"
    assert "queued" not in started
