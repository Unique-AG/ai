from unique_search_proxy.web.core.crawlers.basic.processing.html_markdown import (
    html_to_markdown_async,
)


async def process_html(body: str, *, timeout: float) -> str:
    return await html_to_markdown_async(body, timeout=timeout)
