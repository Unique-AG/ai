from __future__ import annotations

import logging
from urllib.parse import urldefrag, urlsplit, urlunsplit

from markdownify import markdownify

from unique_search_proxy.web.core.schema import WebSearchResult

_LOGGER = logging.getLogger(__name__)


def canonicalize_url(url: str) -> str:
    """Normalize a URL for deduplication (strip fragment, lowercase host)."""
    stripped = url.strip()
    without_fragment, _fragment = urldefrag(stripped)
    parsed = urlsplit(without_fragment)
    hostname = parsed.hostname
    if hostname is None:
        return without_fragment

    normalized_host = hostname.rstrip(".").lower()
    port = f":{parsed.port}" if parsed.port is not None else ""
    credentials = ""
    if parsed.username is not None:
        credentials = parsed.username
        if parsed.password is not None:
            credentials = f"{credentials}:{parsed.password}"
        credentials = f"{credentials}@"

    netloc = f"{credentials}{normalized_host}{port}"

    return urlunsplit(
        (
            parsed.scheme.lower(),
            netloc,
            parsed.path,
            parsed.query,
            "",
        )
    )


def dedupe_results_by_url(results: list[WebSearchResult]) -> list[WebSearchResult]:
    """Drop duplicate results using canonical URL as the key."""
    seen: set[str] = set()
    deduped: list[WebSearchResult] = []
    for result in results:
        key = canonicalize_url(result.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def html_to_markdown(html: str) -> str:
    """Convert HTML to cleaned markdown."""
    try:
        return markdownify(html, heading_style="ATX")
    except Exception:
        _LOGGER.exception("Error converting HTML to markdown")
        return ""
