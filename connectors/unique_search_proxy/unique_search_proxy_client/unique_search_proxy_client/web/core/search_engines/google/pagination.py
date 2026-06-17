from __future__ import annotations

from typing import Iterator

from unique_search_proxy_client.web.core.search_engines.pagination import PageRequest

GOOGLE_MAX_PAGE_SIZE = 10
"""Maximum ``num`` per Google Custom Search request."""

GOOGLE_FIRST_OFFSET = 1
"""Google ``start`` is 1-based."""


def iter_google_page_requests(fetch_size: int) -> Iterator[PageRequest]:
    """Yield Google CSE pages until ``fetch_size`` results have been requested."""
    if fetch_size <= 0:
        return

    collected = 0
    page_index = 0
    offset = GOOGLE_FIRST_OFFSET
    while collected < fetch_size:
        page_index += 1
        count = min(fetch_size - collected, GOOGLE_MAX_PAGE_SIZE)
        yield PageRequest(page_index=page_index, offset=offset, count=count)
        collected += count
        offset += count
