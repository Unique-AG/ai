"""Curated request bodies for Swagger UI (Try it out presets)."""

from __future__ import annotations

from typing import Any

from fastapi.openapi.models import Example

SEARCH_GOOGLE: dict[str, Any] = {
    "engine": "google",
    "query": "unique ag",
    "fetchSize": 10,
    "safe": "active",
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
    "config": {"crawler": "basic"},
    "parallel": True,
    "timeout": 30,
}

CRAWL_BASIC_HTML_MARKDOWN: dict[str, Any] = {
    "urls": ["https://example.com"],
    "config": {
        "crawler": "basic",
        "contentTypeHandlers": {
            "text/html": "allow",
            "application/xhtml+xml": "allow",
        },
    },
    "parallel": True,
    "timeout": 30,
}

GOOGLE_CONFIG_DEFAULT: dict[str, Any] = {
    "engine": "google",
    "fetchSize": 10,
    "safe": "active",
}

GOOGLE_CONFIG_WITH_EXPOSED_GL: dict[str, Any] = {
    "engine": "google",
    "fetchSize": 10,
    "safe": "active",
    "gl": {"expose": True, "value": "ch"},
    "dateRestrict": {"expose": False, "value": "d7"},
}

SEARCH_ENGINE_CALL_SCHEMA_OPENAPI_EXAMPLES: dict[str, Example] = {
    "default_projection": Example(
        summary="Call schema (query + fetchSize only)",
        description="Default LLM projection when optional params are not exposed.",
        value=GOOGLE_CONFIG_DEFAULT,
    ),
    "with_exposed_params": Example(
        summary="Call schema (+ gl)",
        description="`gl.expose=true` adds `gl` to the LLM call schema; `dateRestrict` stays merge-only.",
        value=GOOGLE_CONFIG_WITH_EXPOSED_GL,
    ),
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
