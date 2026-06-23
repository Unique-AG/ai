"""Crawl payload presets for Swagger and dev CLI."""

from __future__ import annotations

from unique_search_proxy_client.web.presets.common import EXAMPLE_URLS_MULTI
from unique_search_proxy_client.web.presets.types import PresetDefinition

CRAWL_PRESETS: tuple[PresetDefinition, ...] = (
    PresetDefinition(
        id="basic_raw",
        summary="Basic crawl (raw body only)",
        description="Returns raw response text and contentType; content stays null.",
        kind="crawl",
        provider_id="Basic",
        overrides={
            "contentTypes": {
                "html": False,
                "xhtml": False,
                "plainText": False,
                "markdown": False,
                "pdf": False,
            },
        },
    ),
    PresetDefinition(
        id="basic_html_markdown",
        summary="Basic crawl (HTML to markdown)",
        description="Processes allowed content types into the content field.",
        kind="crawl",
        provider_id="Basic",
        overrides={
            "contentTypes": {
                "html": True,
                "xhtml": True,
                "plainText": False,
                "markdown": False,
                "pdf": False,
            },
        },
    ),
    PresetDefinition(
        id="basic_multi_url",
        summary="Basic crawl (multi-URL batch)",
        description="Fetches multiple URLs in one request with default content processing.",
        kind="crawl",
        provider_id="Basic",
        overrides={"urls": list(EXAMPLE_URLS_MULTI)},
    ),
    PresetDefinition(
        id="tavily_minimal",
        summary="Tavily extract (minimal)",
        description="Tavily Extract API; requires TAVILY_API_KEY in .env.",
        kind="crawl",
        provider_id="Tavily",
    ),
    PresetDefinition(
        id="tavily_rerank",
        summary="Tavily extract (query rerank)",
        description=(
            "Tavily extract with query reranking and chunks per source. "
            "Requires TAVILY_API_KEY in .env."
        ),
        kind="crawl",
        provider_id="Tavily",
        overrides={
            "query": "main product features",
            "chunksPerSource": 3,
            "includeImages": True,
        },
    ),
    PresetDefinition(
        id="jina_minimal",
        summary="Jina reader (minimal)",
        description="Jina Reader API; requires JINA_API_KEY in .env.",
        kind="crawl",
        provider_id="Jina",
    ),
    PresetDefinition(
        id="jina_selectors",
        summary="Jina reader (selectors + no cache)",
        description=(
            "Jina Reader with CSS selectors and cache bypass. "
            "Requires JINA_API_KEY in .env."
        ),
        kind="crawl",
        provider_id="Jina",
        overrides={
            "removeSelector": ["header", "footer", "nav"],
            "waitForSelector": ["main", "article"],
            "noCache": True,
        },
    ),
    PresetDefinition(
        id="firecrawl_minimal",
        summary="Firecrawl batch scrape (minimal)",
        description=("Firecrawl v2 batch scrape; requires FIRECRAWL_API_KEY in .env."),
        kind="crawl",
        provider_id="Firecrawl",
        overrides={"timeout": 60},
    ),
    PresetDefinition(
        id="firecrawl_enhanced",
        summary="Firecrawl batch scrape (enhanced proxy)",
        description=(
            "Firecrawl with enhanced proxy, mobile emulation, and wait. "
            "Requires FIRECRAWL_API_KEY in .env."
        ),
        kind="crawl",
        provider_id="Firecrawl",
        overrides={
            "proxy": "enhanced",
            "waitFor": 1000,
            "mobile": True,
            "timeout": 90,
        },
    ),
)

__all__ = ["CRAWL_PRESETS"]
