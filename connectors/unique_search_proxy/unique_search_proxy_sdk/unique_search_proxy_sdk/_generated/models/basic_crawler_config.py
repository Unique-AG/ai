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
    from ..models.basic_crawler_config_contenttypehandlers import (
        BasicCrawlerConfigContenttypehandlers,
    )


T = TypeVar("T", bound="BasicCrawlerConfig")


@_attrs_define
class BasicCrawlerConfig:
    """Deployment config for the HTTP basic crawler.

    Attributes:
        crawler (Literal['basic'] | Unset):  Default: 'basic'.
        content_type_handlers (BasicCrawlerConfigContenttypehandlers | Unset): Per media-type policy using exact
            Content-Type values (no parameters). allow: run the built-in processor into ``content``; forbid: return ``raw``
            only. Types not listed are not processed.
        max_concurrent_requests (int | Unset): Maximum concurrent HTTP fetches Default: 10.
        exposed_fields (list[str] | Unset): Call-schema fields exposed to LLM-driven callers (urls always exposed)
    """

    crawler: Literal["basic"] | Unset = "basic"
    content_type_handlers: BasicCrawlerConfigContenttypehandlers | Unset = UNSET
    max_concurrent_requests: int | Unset = 10
    exposed_fields: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        crawler = self.crawler

        content_type_handlers: dict[str, Any] | Unset = UNSET
        if not isinstance(self.content_type_handlers, Unset):
            content_type_handlers = self.content_type_handlers.to_dict()

        max_concurrent_requests = self.max_concurrent_requests

        exposed_fields: list[str] | Unset = UNSET
        if not isinstance(self.exposed_fields, Unset):
            exposed_fields = self.exposed_fields

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if crawler is not UNSET:
            field_dict["crawler"] = crawler
        if content_type_handlers is not UNSET:
            field_dict["contentTypeHandlers"] = content_type_handlers
        if max_concurrent_requests is not UNSET:
            field_dict["maxConcurrentRequests"] = max_concurrent_requests
        if exposed_fields is not UNSET:
            field_dict["exposedFields"] = exposed_fields

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.basic_crawler_config_contenttypehandlers import (
            BasicCrawlerConfigContenttypehandlers,
        )

        d = dict(src_dict)
        crawler = cast(Literal["basic"] | Unset, d.pop("crawler", UNSET))
        if crawler != "basic" and not isinstance(crawler, Unset):
            raise ValueError(f"crawler must match const 'basic', got '{crawler}'")

        _content_type_handlers = d.pop("contentTypeHandlers", UNSET)
        content_type_handlers: BasicCrawlerConfigContenttypehandlers | Unset
        if isinstance(_content_type_handlers, Unset):
            content_type_handlers = UNSET
        else:
            content_type_handlers = BasicCrawlerConfigContenttypehandlers.from_dict(
                _content_type_handlers
            )

        max_concurrent_requests = d.pop("maxConcurrentRequests", UNSET)

        exposed_fields = cast(list[str], d.pop("exposedFields", UNSET))

        basic_crawler_config = cls(
            crawler=crawler,
            content_type_handlers=content_type_handlers,
            max_concurrent_requests=max_concurrent_requests,
            exposed_fields=exposed_fields,
        )

        basic_crawler_config.additional_properties = d
        return basic_crawler_config

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
