"""Build the Firecrawl ``POST /v2/search`` body from a search request."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

from unique_search_proxy_core.errors import BadRequestProxyError
from unique_search_proxy_core.search_engines.firecrawl.schema import (
    FIRECRAWL_MAX_QUERY_LENGTH,
    FIRECRAWL_SOURCES,
    FirecrawlSearchRequest,
)

_LOGGER = logging.getLogger(__name__)

_MS_PER_SECOND = 1000


def build_firecrawl_search_body(
    *,
    query: str,
    request: FirecrawlSearchRequest,  # type: ignore[valid-type]
    enterprise: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble the Firecrawl ``POST /v2/search`` JSON body.

    Args:
        query (str): Search query; cut to Firecrawl's 500-character limit.
        request (FirecrawlSearchRequest): Merged request. Its ``timeout`` is
            in seconds and is sent in milliseconds.
        enterprise (list[str] | None): Zero data retention mode to send, if any.

    Returns:
        dict[str, Any]: The JSON body for Firecrawl.

    Raises:
        BadRequestProxyError: When every include domain is also excluded.
    """
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
        # Leaves out results Firecrawl cannot read itself, so that a
        # Firecrawl Web Page Reader does not fail on them.
        "ignoreInvalidURLs": True,
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

    return body


def _time_based_search(
    request: FirecrawlSearchRequest,  # type: ignore[valid-type]
) -> str | None:
    """Firecrawl ``tbs``: sort by date and the time filter, comma separated."""
    parts = ["sbd:1"] if request.sort_by_date else []
    if request.time_filter is not None:
        parts.append(request.time_filter)
    return ",".join(parts) or None


def _domain_filters(
    *,
    include_domains: list[str] | None,
    exclude_domains: list[str] | None,
) -> dict[str, list[str]]:
    """Return ``includeDomains`` or ``excludeDomains``; Firecrawl rejects both together.

    With an include list, excluded hosts are removed from it. Excluded
    subdomains of an included host cannot be sent: ``is_excluded_url`` drops
    them from the results.
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


def is_excluded_url(url: str, exclude_domains: list[str] | None) -> bool:
    """Tell whether a result URL is on an excluded host or one of its subdomains.

    Args:
        url (str): Result URL.
        exclude_domains (list[str] | None): Excluded hostnames.

    Returns:
        bool: True when the URL's host is excluded.
    """
    if not exclude_domains:
        return False
    host = _normalize_host(urlsplit(url).hostname or "")
    return _is_excluded(host, [_normalize_host(d) for d in exclude_domains])


__all__ = ["build_firecrawl_search_body", "is_excluded_url"]
