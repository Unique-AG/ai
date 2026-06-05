from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="WebSearchResult")


@_attrs_define
class WebSearchResult:
    """Normalized search result used on the curated response path.

    Attributes:
        url (str):
        title (str):
        snippet (str): A short description of the content found on this website
        content (str | Unset): The content of the website Default: ''.
    """

    url: str
    title: str
    snippet: str
    content: str | Unset = ""
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        url = self.url

        title = self.title

        snippet = self.snippet

        content = self.content

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "url": url,
                "title": title,
                "snippet": snippet,
            }
        )
        if content is not UNSET:
            field_dict["content"] = content

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        url = d.pop("url")

        title = d.pop("title")

        snippet = d.pop("snippet")

        content = d.pop("content", UNSET)

        web_search_result = cls(
            url=url,
            title=title,
            snippet=snippet,
            content=content,
        )

        web_search_result.additional_properties = d
        return web_search_result

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
