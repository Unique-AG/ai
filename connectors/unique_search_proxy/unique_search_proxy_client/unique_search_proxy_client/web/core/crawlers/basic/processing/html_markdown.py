from __future__ import annotations

import asyncio

from markdownify import markdownify


def html_to_markdown(html: str) -> str:
    """Convert HTML to cleaned markdown (blocking; use ``html_to_markdown_async`` in async code)."""
    return markdownify(html, heading_style="ATX")


async def html_to_markdown_async(html: str, *, timeout: float) -> str:
    """Run ``html_to_markdown`` in the default thread pool so the event loop stays responsive."""
    return await asyncio.wait_for(
        asyncio.to_thread(html_to_markdown, html),
        timeout=timeout,
    )
