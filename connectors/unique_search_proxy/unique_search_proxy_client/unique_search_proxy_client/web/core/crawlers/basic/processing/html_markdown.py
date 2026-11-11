from __future__ import annotations

import asyncio
import contextvars
from concurrent.futures import ThreadPoolExecutor

from markdownify import markdownify

# Conversion is CPU-bound and holds the GIL, so threads beyond the pod's CPU add
# peak memory without throughput. A pool of its own also keeps the default
# executor, which url-safety DNS lookups use, free while pages convert.
CONVERSION_THREADS = 2

_conversion_pool = ThreadPoolExecutor(
    max_workers=CONVERSION_THREADS,
    thread_name_prefix="html-to-markdown",
)


def html_to_markdown(html: str) -> str:
    """Convert HTML to cleaned markdown (blocking; use ``html_to_markdown_async`` in async code)."""
    return markdownify(html, heading_style="ATX")


async def html_to_markdown_async(html: str, *, timeout: float) -> str:
    """Run ``html_to_markdown`` on the conversion pool so the event loop stays responsive.

    The timeout includes time spent queued; a conversion that times out before
    a thread picks it up never runs.
    """
    context = contextvars.copy_context()

    def convert() -> str:
        return context.run(html_to_markdown, html)

    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(_conversion_pool, convert),
        timeout=timeout,
    )
