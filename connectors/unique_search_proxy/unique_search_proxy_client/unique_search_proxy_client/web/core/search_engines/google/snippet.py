"""Snippet text for one Google Custom Search result."""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from typing import Any

# Description tags in ``pagemap.metatags``, most preferred first.
_DESCRIPTION_KEYS = ("og:description", "twitter:description")
# Values some sites put in a description tag instead of leaving it out.
_PLACEHOLDERS = frozenset({"null", "none", "undefined", "n/a", "nan"})
_WHITESPACE = re.compile(r"\s+")


def build_google_snippet(item: Mapping[str, Any]) -> str:
    """Return the result's snippet, followed by the page's own description.

    Google's ``snippet`` is a short excerpt picked for the query (about 160
    characters). The same result also carries the page's own description in
    ``pagemap.metatags`` (up to about 1,000 characters). For a LinkedIn profile
    that is the headline, the start of the About text, and the experience,
    education and location line. The description goes on its own line after the
    snippet, unless it only repeats the snippet or the title.
    """
    snippet = item.get("snippet") or ""
    description = _page_description(item)
    if not description or _repeats(description, snippet, item.get("title") or ""):
        return snippet
    return f"{snippet}\n{description}" if snippet else description


def _page_description(item: Mapping[str, Any]) -> str:
    pagemap = item.get("pagemap")
    if not isinstance(pagemap, Mapping):
        return ""
    metatags = pagemap.get("metatags")
    if not isinstance(metatags, list):
        return ""
    for key in _DESCRIPTION_KEYS:
        for tags in metatags:
            if not isinstance(tags, Mapping):
                continue
            value = tags.get(key)
            if not isinstance(value, str):
                continue
            text = _normalize(value)
            if text and text.rstrip(".").casefold() not in _PLACEHOLDERS:
                return text
    return ""


def _repeats(description: str, snippet: str, title: str) -> bool:
    needle = description.casefold()
    return (
        needle in _normalize(snippet).casefold()
        or needle in _normalize(title).casefold()
    )


def _normalize(text: str) -> str:
    """Decode HTML entities and collapse whitespace (descriptions keep both)."""
    return _WHITESPACE.sub(" ", html.unescape(text)).strip()
