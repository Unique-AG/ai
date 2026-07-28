from __future__ import annotations

from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypeVar,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.content_types import ContentTypes


T = TypeVar("T", bound="BasicCrawlRequest")


@_attrs_define
class BasicCrawlRequest:
    """
    Attributes:
        urls (list[str]): URLs to crawl
        crawler (Literal['Basic'] | Unset): Provider discriminator; must be `Basic` for this config. Default: 'Basic'.
        timeout (int | Unset): Request timeout in seconds Default: 30.
        content_types (ContentTypes | Unset): Per-type activation flags for basic-crawler content processing.
        max_concurrent_requests (int | Unset): Maximum concurrent HTTP fetches Default: 10.
    """

    urls: list[str]
    crawler: Literal["Basic"] | Unset = "Basic"
    timeout: int | Unset = 30
    content_types: ContentTypes | Unset = UNSET
    max_concurrent_requests: int | Unset = 10
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        urls = self.urls

        crawler = self.crawler

        timeout = self.timeout

        content_types: dict[str, Any] | Unset = UNSET
        if not isinstance(self.content_types, Unset):
            content_types = self.content_types.to_dict()

        max_concurrent_requests = self.max_concurrent_requests

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "urls": urls,
            }
        )
        if crawler is not UNSET:
            field_dict["crawler"] = crawler
        if timeout is not UNSET:
            field_dict["timeout"] = timeout
        if content_types is not UNSET:
            field_dict["contentTypes"] = content_types
        if max_concurrent_requests is not UNSET:
            field_dict["maxConcurrentRequests"] = max_concurrent_requests

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.content_types import ContentTypes

        d = dict(src_dict)
        urls = cast(list[str], d.pop("urls"))

        crawler = cast(Literal["Basic"] | Unset, d.pop("crawler", UNSET))
        if crawler != "Basic" and not isinstance(crawler, Unset):
            raise ValueError(f"crawler must match const 'Basic', got '{crawler}'")

        timeout = d.pop("timeout", UNSET)

        _content_types = d.pop("contentTypes", UNSET)
        content_types: ContentTypes | Unset
        if isinstance(_content_types, Unset):
            content_types = UNSET
        else:
            content_types = ContentTypes.from_dict(_content_types)

        max_concurrent_requests = d.pop("maxConcurrentRequests", UNSET)

        basic_crawl_request = cls(
            urls=urls,
            crawler=crawler,
            timeout=timeout,
            content_types=content_types,
            max_concurrent_requests=max_concurrent_requests,
        )

        basic_crawl_request.additional_properties = d
        return basic_crawl_request

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
