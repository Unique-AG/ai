"""Curated request bodies for Swagger UI (Try it out presets)."""

from __future__ import annotations

from typing import Any

from fastapi.openapi.models import Example

SEARCH_GOOGLE_SNIPPETS: dict[str, Any] = {
    "config": {
        "engine": "google",
        "fetchSize": 10,
        "safe": "active",
        "exposedFields": [],
    },
    "call": {"query": "unique ag"},
    "includeContent": False,
    "timeout": 30,
}

SEARCH_GOOGLE_WITH_CONTENT: dict[str, Any] = {
    "config": {
        "engine": "google",
        "fetchSize": 5,
        "safe": "active",
        "exposedFields": [],
    },
    "call": {"query": "unique ag"},
    "includeContent": True,
    "crawlerConfig": {
        "crawler": "basic",
        "contentTypeHandlers": {
            "text/html": "allow",
            "application/xhtml+xml": "allow",
        },
    },
    "timeout": 60,
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

SEARCH_CALL_SCHEMA_GOOGLE_MINIMAL: dict[str, Any] = {
    "config": {
        "engine": "google",
        "fetchSize": 10,
        "safe": "active",
        "exposedFields": [],
    },
}

SEARCH_CALL_SCHEMA_GOOGLE_WITH_GL: dict[str, Any] = {
    "config": {
        "engine": "google",
        "fetchSize": 10,
        "gl": "ch",
        "exposedFields": ["gl", "dateRestrict"],
        "dateRestrict": "m1",
    },
}

SEARCH_CALL_SCHEMA_OPENAPI_EXAMPLES: dict[str, Example] = {
    "google_query_only": Example(
        summary="Google call schema (query only)",
        description="Default exposure: only query is LLM-visible.",
        value=SEARCH_CALL_SCHEMA_GOOGLE_MINIMAL,
    ),
    "google_with_optional_params": Example(
        summary="Google call schema (+ gl, dateRestrict)",
        description="exposedFields adds optional invocation knobs to the returned JSON Schema.",
        value=SEARCH_CALL_SCHEMA_GOOGLE_WITH_GL,
    ),
}

SEARCH_OPENAPI_EXAMPLES: dict[str, Example] = {
    "google_snippets": Example(
        summary="Google search (snippets only)",
        description="Minimal config; requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID in .env.",
        value=SEARCH_GOOGLE_SNIPPETS,
    ),
    "google_with_content": Example(
        summary="Google search + basic crawler fill",
        description="Sets includeContent and a basic crawler with HTML markdown processing.",
        value=SEARCH_GOOGLE_WITH_CONTENT,
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
