"""Snippet text for one Google Custom Search result."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from typing import Any

_DESCRIPTION_KEYS = ("og:description", "twitter:description")
_PLACEHOLDERS = frozenset({"null", "none"})
_WHITESPACE = re.compile(r"\s+")


def build_google_snippet(item: Mapping[str, Any]) -> str:
    """Return the snippet, followed by the page description from ``pagemap.metatags``."""
    snippet = item.get("snippet") or ""
    description = _page_description(item)
    if not description:
        return snippet
    return f"{snippet}\n{description}" if snippet else description


def _page_description(item: Mapping[str, Any]) -> str:
    pagemap = item.get("pagemap")
    metatags = pagemap.get("metatags") if isinstance(pagemap, Mapping) else None
    tags = metatags[0] if isinstance(metatags, list) and metatags else None
    if not isinstance(tags, Mapping):
        return ""
    for key in _DESCRIPTION_KEYS:
        value = tags.get(key)
        text = _normalize(value) if isinstance(value, str) else ""
        if text and text.rstrip(".").casefold() not in _PLACEHOLDERS:
            return text
    return ""


def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", html.unescape(text)).strip()
