from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.crawl_url_result import CrawlUrlResult


T = TypeVar("T", bound="CrawlResponse")


@_attrs_define
class CrawlResponse:
    """
    Attributes:
        crawler_type (str):
        results (list[CrawlUrlResult]):
    """

    crawler_type: str
    results: list[CrawlUrlResult]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        crawler_type = self.crawler_type

        results = []
        for results_item_data in self.results:
            results_item = results_item_data.to_dict()
            results.append(results_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "crawlerType": crawler_type,
                "results": results,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.crawl_url_result import CrawlUrlResult

        d = dict(src_dict)
        crawler_type = d.pop("crawlerType")

        results = []
        _results = d.pop("results")
        for results_item_data in _results:
            results_item = CrawlUrlResult.from_dict(results_item_data)

            results.append(results_item)

        crawl_response = cls(
            crawler_type=crawler_type,
            results=results,
        )

        crawl_response.additional_properties = d
        return crawl_response

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
