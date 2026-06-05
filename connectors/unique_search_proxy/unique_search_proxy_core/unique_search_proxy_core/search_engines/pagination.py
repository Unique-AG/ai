from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

DEFAULT_MAX_PAGE_SIZE = 10


@dataclass(frozen=True)
class PageRequest:
    """One page to fetch from an upstream search API."""

    page_index: int
    offset: int
    count: int


def iter_page_requests(
    fetch_size: int,
    *,
    max_page_size: int = DEFAULT_MAX_PAGE_SIZE,
    first_offset: int = 1,
) -> Iterator[PageRequest]:
    """Yield page requests until ``fetch_size`` results have been requested."""
    if fetch_size <= 0:
        return

    collected = 0
    page_index = 0
    offset = first_offset
    while collected < fetch_size:
        page_index += 1
        count = min(fetch_size - collected, max_page_size)
        yield PageRequest(page_index=page_index, offset=offset, count=count)
        collected += count
        offset += count
