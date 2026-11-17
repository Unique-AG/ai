from __future__ import annotations

from typing import Any

import pytest

from unique_search_proxy_client.web.core.search_engines.google.snippet import (
    build_google_snippet,
)

_SNIPPET = (
    "Oct 21, 2026 ... Jane Doe leads the private banking team at Example Bank ..."
)
_DESCRIPTION = (
    "Head of Private Banking at Example Bank · Experience: Example Bank · "
    "Education: University of Zurich · Location: Zurich"
)


def _item(*, metatags: Any = None, **fields: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "link": "https://www.example.com/people/jane-doe",
        "title": "Jane Doe - Example Bank",
        "snippet": _SNIPPET,
        **fields,
    }
    if metatags is not None:
        item["pagemap"] = {"metatags": metatags}
    return item


@pytest.mark.ai
def test_build_google_snippet__appends_page_description__when_og_description_present() -> (
    None
):
    """
    Purpose: The page's og:description is added on its own line after Google's snippet.
    Why this matters: The snippet is a short excerpt; the description adds the page's
        own summary for pages we can't crawl.
    Setup summary: Item with og:description; assert snippet, newline, description.
    """
    item = _item(metatags=[{"og:description": _DESCRIPTION}])

    assert build_google_snippet(item) == f"{_SNIPPET}\n{_DESCRIPTION}"


@pytest.mark.ai
def test_build_google_snippet__uses_twitter_description__when_og_description_missing() -> (
    None
):
    """
    Purpose: twitter:description is the fallback when a page has no og:description.
    Why this matters: Some pages only set the twitter tag.
    Setup summary: Item with only twitter:description; assert it is appended.
    """
    item = _item(metatags=[{"twitter:description": _DESCRIPTION}])

    assert build_google_snippet(item) == f"{_SNIPPET}\n{_DESCRIPTION}"


@pytest.mark.ai
def test_build_google_snippet__prefers_og_description__when_both_present() -> None:
    """
    Purpose: og:description wins over twitter:description.
    Why this matters: Keeps the output stable and picks the tag most sites fill in fully.
    Setup summary: Item with both tags; assert only the og value is appended.
    """
    item = _item(
        metatags=[{"og:description": _DESCRIPTION, "twitter:description": "Other text"}]
    )

    assert build_google_snippet(item) == f"{_SNIPPET}\n{_DESCRIPTION}"


@pytest.mark.ai
def test_build_google_snippet__decodes_entities_and_collapses_whitespace() -> None:
    """
    Purpose: HTML entities are decoded and line breaks/runs of spaces collapse to one space.
    Why this matters: Google returns descriptions as found in the page's meta tag,
        often with entities and line breaks, which would add noise.
    Setup summary: Escaped, multi-line description; assert clean single-line text.
    """
    item = _item(
        metatags=[
            {"og:description": "I&#39;m CEO &amp; founder.\n\n  Based in   Zurich."}
        ]
    )

    assert (
        build_google_snippet(item) == f"{_SNIPPET}\nI'm CEO & founder. Based in Zurich."
    )


@pytest.mark.ai
@pytest.mark.parametrize("placeholder", ["null", "None.", "  NULL  ", ""])
def test_build_google_snippet__keeps_snippet_only__when_description_is_placeholder(
    placeholder: str,
) -> None:
    """
    Purpose: Placeholder or empty description values are ignored.
    Why this matters: Some sites (seen on PubMed and a law firm site) emit "None."
        or "null" as their description, which would read as content.
    Setup summary: Placeholder og:description; assert snippet unchanged.
    """
    item = _item(metatags=[{"og:description": placeholder}])

    assert build_google_snippet(item) == _SNIPPET


@pytest.mark.ai
def test_build_google_snippet__falls_back_to_twitter__when_og_description_is_placeholder() -> (
    None
):
    """
    Purpose: A placeholder og:description doesn't block a real twitter:description.
    Why this matters: The fallback should apply whenever og has nothing usable.
    Setup summary: og="null", twitter=real text; assert the twitter text is appended.
    """
    item = _item(
        metatags=[{"og:description": "null", "twitter:description": _DESCRIPTION}]
    )

    assert build_google_snippet(item) == f"{_SNIPPET}\n{_DESCRIPTION}"


@pytest.mark.ai
@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({}, id="no-pagemap"),
        pytest.param({"pagemap": None}, id="pagemap-null"),
        pytest.param({"pagemap": ["not", "a", "dict"]}, id="pagemap-not-dict"),
        pytest.param({"pagemap": {"cse_image": [{"src": "x"}]}}, id="no-metatags"),
        pytest.param({"pagemap": {"metatags": None}}, id="metatags-null"),
        pytest.param({"pagemap": {"metatags": []}}, id="metatags-empty"),
        pytest.param(
            {"pagemap": {"metatags": {"og:description": "x"}}}, id="metatags-not-list"
        ),
        pytest.param(
            {"pagemap": {"metatags": ["text", None]}}, id="metatags-entries-not-dict"
        ),
        pytest.param(
            {"pagemap": {"metatags": [{"og:description": ["x"]}]}}, id="value-not-str"
        ),
    ],
)
def test_build_google_snippet__keeps_snippet_only__when_pagemap_missing_or_malformed(
    fields: dict[str, Any],
) -> None:
    """
    Purpose: Missing or unexpectedly shaped pagemap data leaves the snippet unchanged.
    Why this matters: pagemap is optional and loosely typed; it must never break a search.
    Setup summary: Items with absent/malformed pagemap; assert snippet unchanged, no error.
    """
    item = _item(**fields)

    assert build_google_snippet(item) == _SNIPPET


@pytest.mark.ai
@pytest.mark.parametrize("snippet_fields", [{"snippet": ""}, {"snippet": None}, {}])
def test_build_google_snippet__returns_description_only__when_snippet_missing(
    snippet_fields: dict[str, Any],
) -> None:
    """
    Purpose: Results without a snippet get the description alone, with no leading newline.
    Why this matters: Google omits the snippet for some pages (e.g. Zefix entries).
    Setup summary: Item without snippet but with og:description; assert description only.
    """
    item = _item(metatags=[{"og:description": _DESCRIPTION}])
    item.pop("snippet")
    item.update(snippet_fields)

    assert build_google_snippet(item) == _DESCRIPTION
