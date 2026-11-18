from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ProvidersListResponse")


@_attrs_define
class ProvidersListResponse:
    """
    Attributes:
        search_engines (list[str]): Registered search engine ids (config discriminator values)
        crawlers (list[str]): Registered crawler ids (config discriminator values)
        agent_engines (list[str] | Unset): Registered agent search engine ids (config discriminator values)
        crawling_enabled (bool | Unset): Whether POST /v1/crawl accepts requests. False fetches nothing. Default: True.
    """

    search_engines: list[str]
    crawlers: list[str]
    agent_engines: list[str] | Unset = UNSET
    crawling_enabled: bool | Unset = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        search_engines = self.search_engines

        crawlers = self.crawlers

        agent_engines: list[str] | Unset = UNSET
        if not isinstance(self.agent_engines, Unset):
            agent_engines = self.agent_engines

        crawling_enabled = self.crawling_enabled

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "searchEngines": search_engines,
                "crawlers": crawlers,
            }
        )
        if agent_engines is not UNSET:
            field_dict["agentEngines"] = agent_engines
        if crawling_enabled is not UNSET:
            field_dict["crawlingEnabled"] = crawling_enabled

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        search_engines = cast(list[str], d.pop("searchEngines"))

        crawlers = cast(list[str], d.pop("crawlers"))

        agent_engines = cast(list[str], d.pop("agentEngines", UNSET))

        crawling_enabled = d.pop("crawlingEnabled", UNSET)

        providers_list_response = cls(
            search_engines=search_engines,
            crawlers=crawlers,
            agent_engines=agent_engines,
            crawling_enabled=crawling_enabled,
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
