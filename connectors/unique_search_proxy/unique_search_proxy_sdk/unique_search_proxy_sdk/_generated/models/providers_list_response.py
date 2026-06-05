from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ProvidersListResponse")


@_attrs_define
class ProvidersListResponse:
    """
    Attributes:
        search_engines (list[str]): Registered search engine ids (config discriminator values)
        crawlers (list[str]): Registered crawler ids (config discriminator values)
    """

    search_engines: list[str]
    crawlers: list[str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        search_engines = self.search_engines

        crawlers = self.crawlers

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "searchEngines": search_engines,
                "crawlers": crawlers,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        search_engines = cast(list[str], d.pop("searchEngines"))

        crawlers = cast(list[str], d.pop("crawlers"))

        providers_list_response = cls(
            search_engines=search_engines,
            crawlers=crawlers,
        )

        providers_list_response.additional_properties = d
        return providers_list_response

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
