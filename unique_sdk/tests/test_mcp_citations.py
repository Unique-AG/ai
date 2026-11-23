"""Shared MCP citation extractor, outside the CLI."""

from __future__ import annotations

from unique_sdk.utils.mcp_citations import extract_mcp_citation_items


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
