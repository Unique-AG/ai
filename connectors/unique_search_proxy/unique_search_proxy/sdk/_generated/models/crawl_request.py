from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.basic_crawler_config import BasicCrawlerConfig


T = TypeVar("T", bound="CrawlRequest")


@_attrs_define
class CrawlRequest:
    """
    Attributes:
        urls (list[str]): URLs to crawl
        config (BasicCrawlerConfig): Deployment config for the HTTP basic crawler.
        accepted_content_types (list[str] | None | Unset): Optional hint for callers (e.g. text/html). The proxy does
            not filter on this; consumers decide how to handle each result's contentType.
        parallel (bool | Unset): Whether to crawl URLs concurrently Default: True.
        timeout (int | Unset): Per-request timeout in seconds Default: 30.
    """

    urls: list[str]
    config: BasicCrawlerConfig
    accepted_content_types: list[str] | None | Unset = UNSET
    parallel: bool | Unset = True
    timeout: int | Unset = 30
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        urls = self.urls

        config = self.config.to_dict()

        accepted_content_types: list[str] | None | Unset
        if isinstance(self.accepted_content_types, Unset):
            accepted_content_types = UNSET
        elif isinstance(self.accepted_content_types, list):
            accepted_content_types = self.accepted_content_types

        else:
            accepted_content_types = self.accepted_content_types

        parallel = self.parallel

        timeout = self.timeout

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "urls": urls,
                "config": config,
            }
        )
        if accepted_content_types is not UNSET:
            field_dict["acceptedContentTypes"] = accepted_content_types
        if parallel is not UNSET:
            field_dict["parallel"] = parallel
        if timeout is not UNSET:
            field_dict["timeout"] = timeout

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.basic_crawler_config import BasicCrawlerConfig

        d = dict(src_dict)
        urls = cast(list[str], d.pop("urls"))

        config = BasicCrawlerConfig.from_dict(d.pop("config"))

        def _parse_accepted_content_types(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                accepted_content_types_type_0 = cast(list[str], data)

                return accepted_content_types_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        accepted_content_types = _parse_accepted_content_types(
            d.pop("acceptedContentTypes", UNSET)
        )

        parallel = d.pop("parallel", UNSET)

        timeout = d.pop("timeout", UNSET)

        crawl_request = cls(
            urls=urls,
            config=config,
            accepted_content_types=accepted_content_types,
            parallel=parallel,
            timeout=timeout,
        )

        crawl_request.additional_properties = d
        return crawl_request

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
