"""Curated request bodies for Swagger UI (Try it out presets)."""

from __future__ import annotations

from typing import Any

from fastapi.openapi.models import Example
from unique_search_proxy_core.crawlers.base import CrawlerType

SEARCH_GOOGLE: dict[str, Any] = {
    "engine": "google",
    "query": "unique ag",
    "fetchSize": 10,
    "safe": "active",
    "timeout": 30,
}

SEARCH_PERPLEXITY: dict[str, Any] = {
    "engine": "perplexity",
    "query": "unique ag",
    "fetchSize": 10,
    "timeout": 30,
}

SEARCH_GOOGLE_WITH_GL: dict[str, Any] = {
    "engine": "google",
    "query": "unique ag",
    "fetchSize": 10,
    "gl": "ch",
    "dateRestrict": "d7",
    "safe": "active",
    "timeout": 30,
}

CRAWL_BASIC_RAW: dict[str, Any] = {
    "urls": ["https://example.com"],
    "crawler": CrawlerType.BASIC.value,
    "contentTypes": {
        "html": False,
        "xhtml": False,
        "plainText": False,
        "markdown": False,
        "pdf": False,
    },
    "timeout": 30,
}

CRAWL_BASIC_HTML_MARKDOWN: dict[str, Any] = {
    "urls": ["https://example.com"],
    "crawler": CrawlerType.BASIC.value,
    "contentTypes": {
        "html": True,
        "xhtml": True,
    },
    "timeout": 30,
}

SEARCH_OPENAPI_EXAMPLES: dict[str, Example] = {
    "google_search": Example(
        summary="Google search",
        description="Flat search request; requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID in .env.",
        value=SEARCH_GOOGLE,
    ),
    "google_search_with_gl": Example(
        summary="Google search (with gl and dateRestrict)",
        description="Full execution payload including optional provider parameters.",
        value=SEARCH_GOOGLE_WITH_GL,
    ),
    "perplexity_search": Example(
        summary="Perplexity search",
        description="Flat search request; requires PERPLEXITY_SEARCH_API_KEY in .env.",
        value=SEARCH_PERPLEXITY,
    ),
}

CRAWL_OPENAPI_EXAMPLES: dict[str, Example] = {
    "basic_raw": Example(
        summary="Basic crawl (raw body only)",
        description="Returns raw response text and contentType; content stays null.",
        value=CRAWL_BASIC_RAW,
    ),
    "basic_html_markdown": Example(
        summary="Basic crawl (HTML to markdown)",
        description="Processes allowed content types into the content field.",
        value=CRAWL_BASIC_HTML_MARKDOWN,
    ),
}
