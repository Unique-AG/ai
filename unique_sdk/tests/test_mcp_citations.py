"""Shared MCP citation extractor, outside the CLI."""

from __future__ import annotations

import json

import pytest

from unique_sdk.utils.mcp_citations import (
    extract_mcp_citation_items,
    find_embedded_json,
)


class _TypedUrl:
    """Mirrors pydantic's ``AnyUrl``: not a ``str``, renders as the URL."""

    def __init__(self, url: str) -> None:
        self._url = url

    def __str__(self) -> str:
        return self._url


class _TypedResourceLink:
    """Mirrors ``mcp.types.ResourceLink``, whose ``uri`` is an ``AnyUrl``."""

    type = "resource_link"

    def __init__(self, name: str, uri: _TypedUrl) -> None:
        self.name = name
        self.uri = uri
        self.description = None


def test_typed_resource_link_keeps_its_https_uri() -> None:
    url = "https://example.com/docs/auth"
    response = {"content": [_TypedResourceLink("Auth overview", _TypedUrl(url))]}

    items = extract_mcp_citation_items(response)

    assert [(item["title"], item.get("url")) for item in items] == [
        ("Auth overview", url)
    ]


def test_find_embedded_json_returns_the_span_of_the_json() -> None:
    text = '[IMPORTANT: cite]\n{"a": 1}\nfooter'

    value, start, end = find_embedded_json(text) or (None, 0, 0)

    assert value == {"a": 1}
    assert (text[:start], text[end:]) == ("[IMPORTANT: cite]\n", "\nfooter")


_INTERNAL = "unique://content/cont_abc"


def _json_response(record: dict) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(record)}]}


@pytest.mark.ai
def test_json_record_keeps_internal_url() -> None:
    items = extract_mcp_citation_items(
        _json_response({"title": "Doc", "url": _INTERNAL})
    )

    assert [(item["title"], item.get("url")) for item in items] == [("Doc", _INTERNAL)]


@pytest.mark.ai
def test_resource_link_keeps_internal_uri() -> None:
    response = {"content": [{"type": "resource_link", "name": "Doc", "uri": _INTERNAL}]}

    items = extract_mcp_citation_items(response)

    assert [(item["title"], item.get("url")) for item in items] == [("Doc", _INTERNAL)]


@pytest.mark.ai
def test_url_path_mapping_keeps_internal_url() -> None:
    response = _json_response({"t": "Doc", "links": {"web": _INTERNAL}})
    mapping = {"titlePath": "t", "urlPath": "links.web"}

    items = extract_mcp_citation_items(response, reference_mapping=mapping)

    assert [(item["title"], item.get("url")) for item in items] == [("Doc", _INTERNAL)]


@pytest.mark.ai
@pytest.mark.parametrize(
    "url", ["ftp://x", "unique://other/x", "unique://content/?view=preview"]
)
def test_other_schemes_are_dropped(url: str) -> None:
    from_json = extract_mcp_citation_items(_json_response({"title": "Doc", "url": url}))
    from_link = extract_mcp_citation_items(
        {"content": [{"type": "resource_link", "name": "Doc", "uri": url}]}
    )

    assert [(item["title"], item.get("url")) for item in from_json] == [("Doc", None)]
    assert [(item["title"], item.get("url")) for item in from_link] == [("Doc", None)]
