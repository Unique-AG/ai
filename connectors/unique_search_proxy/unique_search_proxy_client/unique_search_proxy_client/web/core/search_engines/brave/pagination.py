from __future__ import annotations

from typing import Iterator

from unique_search_proxy_client.web.core.search_engines.pagination import PageRequest

BRAVE_MAX_PAGE_SIZE = 20
"""Maximum ``count`` per Brave web search request."""

BRAVE_MAX_OFFSET = 9
"""Maximum ``offset`` (zero-based page index) per Brave web search API."""


def iter_brave_page_requests(fetch_size: int) -> Iterator[PageRequest]:
    """Yield Brave web-search pages until ``fetch_size`` web results are requested.

    Brave ``offset`` is a **page index** (0, 1, 2, …), not a result offset.
    Increment by 1 per page; never pass cumulative result counts as ``offset``.
    """
    if fetch_size <= 0:
        return

    collected = 0
    page_index = 0
    offset = 0
    while collected < fetch_size and offset <= BRAVE_MAX_OFFSET:
        page_index += 1
        count = min(fetch_size - collected, BRAVE_MAX_PAGE_SIZE)
        yield PageRequest(page_index=page_index, offset=offset, count=count)
        collected += count
        offset += 1
