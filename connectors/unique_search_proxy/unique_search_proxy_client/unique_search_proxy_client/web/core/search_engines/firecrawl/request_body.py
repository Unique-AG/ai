from __future__ import annotations

import logging
from typing import Any

from unique_search_proxy_core.errors import BadRequestProxyError
from unique_search_proxy_core.search_engines.firecrawl.schema import (
    FIRECRAWL_MAX_QUERY_LENGTH,
    FIRECRAWL_SOURCES,
    FirecrawlSearchRequest,
)

from unique_search_proxy_client.web.core.firecrawl_parsers import firecrawl_parsers

_LOGGER = logging.getLogger(__name__)

_MS_PER_SECOND = 1000


def build_firecrawl_search_body(
    *,
    query: str,
    request: FirecrawlSearchRequest,  # type: ignore[valid-type]
    enterprise: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble the Firecrawl ``POST /v2/search`` JSON body from the derived request."""
    if len(query) > FIRECRAWL_MAX_QUERY_LENGTH:
        _LOGGER.warning(
            "Firecrawl accepts queries of at most %s characters; truncating from %s",
            FIRECRAWL_MAX_QUERY_LENGTH,
            len(query),
        )
        query = query[:FIRECRAWL_MAX_QUERY_LENGTH]

    body: dict[str, Any] = {
        "query": query,
        "limit": request.fetch_size,
        "sources": list(FIRECRAWL_SOURCES[request.sources]),
        "timeout": request.timeout * _MS_PER_SECOND,
        "ignoreInvalidURLs": request.ignore_invalid_urls,
    }

    if enterprise:
        body["enterprise"] = enterprise
    # Both are sent only when they differ from Firecrawl's default, so a
    # default search has the same body as before these options existed.
    if not request.highlights:
        body["highlights"] = False
    if request.safe_search:
        body["safe"] = True
    tbs = _time_based_search(request)
    if tbs is not None:
        body["tbs"] = tbs
    if request.category is not None:
        body["categories"] = [request.category]
    if request.country is not None:
        body["country"] = request.country
    if request.location is not None:
        body["location"] = request.location

    body.update(
        _domain_filters(
            include_domains=request.include_domains,
            exclude_domains=request.exclude_domains,
        )
    )

    if request.scrape_results:
        body["scrapeOptions"] = _scrape_options(request)

    return body


def _time_based_search(
    request: FirecrawlSearchRequest,  # type: ignore[valid-type]
) -> str | None:
    """Firecrawl ``tbs``: sort by date and the time filter, comma separated."""
    parts = ["sbd:1"] if request.sort_by_date else []
    if request.time_filter is not None:
        parts.append(request.time_filter)
    return ",".join(parts) or None


def _scrape_options(
    request: FirecrawlSearchRequest,  # type: ignore[valid-type]
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "formats": [{"type": "markdown"}],
        "onlyMainContent": request.only_main_content,
        "removeBase64Images": True,
    }
    if request.max_cache_age_seconds is not None:
        options["maxAge"] = request.max_cache_age_seconds * _MS_PER_SECOND
    parsers = firecrawl_parsers(request.max_pdf_pages)
    if parsers is not None:
        options["parsers"] = parsers
    return options


def _domain_filters(
    *,
    include_domains: list[str] | None,
    exclude_domains: list[str] | None,
) -> dict[str, list[str]]:
    """Return ``includeDomains`` or ``excludeDomains``; Firecrawl rejects both together.

    An include list already limits the search to its hosts, so excluded hosts are
    removed from it instead of being sent separately.
    """
    excluded = [_normalize_host(host) for host in exclude_domains or []]
    if include_domains:
        included = [
            host
            for host in (_normalize_host(host) for host in include_domains)
            if not _is_excluded(host, excluded)
        ]
        if not included:
            raise BadRequestProxyError(
                "Every include domain is also excluded; refusing to search without a domain filter",
            )
        return {"includeDomains": included}
    if excluded:
        return {"excludeDomains": excluded}
    return {}


def _normalize_host(host: str) -> str:
    return host.strip().lower().rstrip(".")


def _is_excluded(host: str, excluded: list[str]) -> bool:
    return any(host == blocked or host.endswith(f".{blocked}") for blocked in excluded)


__all__ = ["build_firecrawl_search_body"]
