from __future__ import annotations

from collections.abc import Mapping
from typing import (
    Any,
    Literal,
    TypeVar,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.tavily_crawl_request_extract_depth import TavilyCrawlRequestExtractDepth
from ..models.tavily_crawl_request_output_format import TavilyCrawlRequestOutputFormat
from ..types import UNSET, Unset

T = TypeVar("T", bound="TavilyCrawlRequest")


@_attrs_define
class TavilyCrawlRequest:
    """
    Attributes:
        urls (list[str]): URLs to crawl
        crawler (Literal['Tavily'] | Unset): Provider discriminator; must be `Tavily` for this config. Default:
            'Tavily'.
        timeout (int | Unset): Request timeout in seconds Default: 30.
        extract_depth (TavilyCrawlRequestExtractDepth | Unset): Tavily extract depth: `basic` or `advanced`. Advanced
            retrieves more data (tables, embedded content) with higher success. Default:
            TavilyCrawlRequestExtractDepth.ADVANCED.
        format_ (TavilyCrawlRequestOutputFormat | Unset): Extracted content format: `markdown` or `text`. Default:
            TavilyCrawlRequestOutputFormat.MARKDOWN.
        query (None | str | Unset): User intent for reranking extracted content chunks. When set, `chunks_per_source`
            may be used.
        chunks_per_source (int | None | Unset): Max relevant chunks per URL when `query` is set (1–5). Chunks appear in
            `raw_content` separated by `[...]`.
        include_images (bool | Unset): Include extracted image URLs in the Tavily response. Default: False.
        include_favicon (bool | Unset): Include the favicon URL for each extracted result. Default: False.
        include_usage (bool | Unset): Include Tavily credit usage information in the response. Default: False.
    """

    urls: list[str]
    crawler: Literal["Tavily"] | Unset = "Tavily"
    timeout: int | Unset = 30
    extract_depth: TavilyCrawlRequestExtractDepth | Unset = (
        TavilyCrawlRequestExtractDepth.ADVANCED
    )
    format_: TavilyCrawlRequestOutputFormat | Unset = (
        TavilyCrawlRequestOutputFormat.MARKDOWN
    )
    query: None | str | Unset = UNSET
    chunks_per_source: int | None | Unset = UNSET
    include_images: bool | Unset = False
    include_favicon: bool | Unset = False
    include_usage: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        urls = self.urls

        crawler = self.crawler

        timeout = self.timeout

        extract_depth: str | Unset = UNSET
        if not isinstance(self.extract_depth, Unset):
            extract_depth = self.extract_depth.value

        format_: str | Unset = UNSET
        if not isinstance(self.format_, Unset):
            format_ = self.format_.value

        query: None | str | Unset
        if isinstance(self.query, Unset):
            query = UNSET
        else:
            query = self.query

        chunks_per_source: int | None | Unset
        if isinstance(self.chunks_per_source, Unset):
            chunks_per_source = UNSET
        else:
            chunks_per_source = self.chunks_per_source

        include_images = self.include_images

        include_favicon = self.include_favicon

        include_usage = self.include_usage

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
        if extract_depth is not UNSET:
            field_dict["extractDepth"] = extract_depth
        if format_ is not UNSET:
            field_dict["format"] = format_
        if query is not UNSET:
            field_dict["query"] = query
        if chunks_per_source is not UNSET:
            field_dict["chunksPerSource"] = chunks_per_source
        if include_images is not UNSET:
            field_dict["includeImages"] = include_images
        if include_favicon is not UNSET:
            field_dict["includeFavicon"] = include_favicon
        if include_usage is not UNSET:
            field_dict["includeUsage"] = include_usage

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        urls = cast(list[str], d.pop("urls"))

        crawler = cast(Literal["Tavily"] | Unset, d.pop("crawler", UNSET))
        if crawler != "Tavily" and not isinstance(crawler, Unset):
            raise ValueError(f"crawler must match const 'Tavily', got '{crawler}'")

        timeout = d.pop("timeout", UNSET)

        _extract_depth = d.pop("extractDepth", UNSET)
        extract_depth: TavilyCrawlRequestExtractDepth | Unset
        if isinstance(_extract_depth, Unset):
            extract_depth = UNSET
        else:
            extract_depth = TavilyCrawlRequestExtractDepth(_extract_depth)

        _format_ = d.pop("format", UNSET)
        format_: TavilyCrawlRequestOutputFormat | Unset
        if isinstance(_format_, Unset):
            format_ = UNSET
        else:
            format_ = TavilyCrawlRequestOutputFormat(_format_)

        def _parse_query(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        query = _parse_query(d.pop("query", UNSET))

        def _parse_chunks_per_source(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        chunks_per_source = _parse_chunks_per_source(d.pop("chunksPerSource", UNSET))

        include_images = d.pop("includeImages", UNSET)

        include_favicon = d.pop("includeFavicon", UNSET)

        include_usage = d.pop("includeUsage", UNSET)

        tavily_crawl_request = cls(
            urls=urls,
            crawler=crawler,
            timeout=timeout,
            extract_depth=extract_depth,
            format_=format_,
            query=query,
            chunks_per_source=chunks_per_source,
            include_images=include_images,
            include_favicon=include_favicon,
            include_usage=include_usage,
        )

        tavily_crawl_request.additional_properties = d
        return tavily_crawl_request

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
