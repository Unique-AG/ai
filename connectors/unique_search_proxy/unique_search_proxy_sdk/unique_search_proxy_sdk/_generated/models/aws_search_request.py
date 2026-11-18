from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import (
    Any,
    Literal,
    TypeVar,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AwsSearchRequest")


@_attrs_define
class AwsSearchRequest:
    """
    Attributes:
        query (str): Search query string
        engine (Literal['aws'] | Unset): Provider discriminator; must be `aws` for this config. Default: 'aws'.
        fetch_size (int | Unset): Default result count sent as InvokeWebSearch maxResults. AWS accepts 1 to 25. Default:
            10.
        timeout (int | Unset): Request timeout in seconds Default: 30.
        include_domains (list[str] | None | Unset): Only search and read these domains. A domain covers its subdomains:
            `snb.ch` also matches `www.snb.ch`. Up to 100.
        exclude_domains (list[str] | None | Unset): Never search or read these domains. A domain covers its subdomains:
            `wikipedia.org` also blocks `en.wikipedia.org`. Up to 100.
        published_after (datetime.datetime | None | Unset): Keep pages AWS dates at or after this time. AWS dates a page
            by when it last changed, so an older document on an updated page still passes. Exposed to the model so it can
            narrow the range per query.
        published_before (datetime.datetime | None | Unset): Keep pages AWS dates at or before this time. AWS dates a
            page by when it last changed, not by the date in the document. Exposed to the model so it can narrow the range
            per query.
    """

    query: str
    engine: Literal["aws"] | Unset = "aws"
    fetch_size: int | Unset = 10
    timeout: int | Unset = 30
    include_domains: list[str] | None | Unset = UNSET
    exclude_domains: list[str] | None | Unset = UNSET
    published_after: datetime.datetime | None | Unset = UNSET
    published_before: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        engine = self.engine

        fetch_size = self.fetch_size

        timeout = self.timeout

        include_domains: list[str] | None | Unset
        if isinstance(self.include_domains, Unset):
            include_domains = UNSET
        elif isinstance(self.include_domains, list):
            include_domains = self.include_domains

        else:
            include_domains = self.include_domains

        exclude_domains: list[str] | None | Unset
        if isinstance(self.exclude_domains, Unset):
            exclude_domains = UNSET
        elif isinstance(self.exclude_domains, list):
            exclude_domains = self.exclude_domains

        else:
            exclude_domains = self.exclude_domains

        published_after: None | str | Unset
        if isinstance(self.published_after, Unset):
            published_after = UNSET
        elif isinstance(self.published_after, datetime.datetime):
            published_after = self.published_after.isoformat()
        else:
            published_after = self.published_after

        published_before: None | str | Unset
        if isinstance(self.published_before, Unset):
            published_before = UNSET
        elif isinstance(self.published_before, datetime.datetime):
            published_before = self.published_before.isoformat()
        else:
            published_before = self.published_before

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if engine is not UNSET:
            field_dict["engine"] = engine
        if fetch_size is not UNSET:
            field_dict["fetchSize"] = fetch_size
        if timeout is not UNSET:
            field_dict["timeout"] = timeout
        if include_domains is not UNSET:
            field_dict["includeDomains"] = include_domains
        if exclude_domains is not UNSET:
            field_dict["excludeDomains"] = exclude_domains
        if published_after is not UNSET:
            field_dict["publishedAfter"] = published_after
        if published_before is not UNSET:
            field_dict["publishedBefore"] = published_before

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        engine = cast(Literal["aws"] | Unset, d.pop("engine", UNSET))
        if engine != "aws" and not isinstance(engine, Unset):
            raise ValueError(f"engine must match const 'aws', got '{engine}'")

        fetch_size = d.pop("fetchSize", UNSET)

        timeout = d.pop("timeout", UNSET)

        def _parse_include_domains(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                include_domains_type_0 = cast(list[str], data)

                return include_domains_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        include_domains = _parse_include_domains(d.pop("includeDomains", UNSET))

        def _parse_exclude_domains(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                exclude_domains_type_0 = cast(list[str], data)

                return exclude_domains_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        exclude_domains = _parse_exclude_domains(d.pop("excludeDomains", UNSET))

        def _parse_published_after(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                published_after_type_0 = datetime.datetime.fromisoformat(data)

                return published_after_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        published_after = _parse_published_after(d.pop("publishedAfter", UNSET))

        def _parse_published_before(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                published_before_type_0 = datetime.datetime.fromisoformat(data)

                return published_before_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        published_before = _parse_published_before(d.pop("publishedBefore", UNSET))

        aws_search_request = cls(
            query=query,
            engine=engine,
            fetch_size=fetch_size,
            timeout=timeout,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            published_after=published_after,
            published_before=published_before,
        )

        aws_search_request.additional_properties = d
        return aws_search_request

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
