from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageRequest:
    """One page to fetch from an upstream search API."""

    page_index: int
    offset: int
    count: int
