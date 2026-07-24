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

from ..models.firecrawl_crawl_request_proxy_mode import FirecrawlCrawlRequestProxyMode
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.firecrawl_crawl_request_scrape_headers_type_0 import (
        FirecrawlCrawlRequestScrapeHeadersType0,
    )


T = TypeVar("T", bound="FirecrawlCrawlRequest")


@_attrs_define
class FirecrawlCrawlRequest:
    """
    Attributes:
        urls (list[str]): URLs to crawl
        crawler (Literal['Firecrawl'] | Unset): Provider discriminator; must be `Firecrawl` for this config. Default:
            'Firecrawl'.
        timeout (int | Unset): Request timeout in seconds Default: 30.
        only_main_content (bool | Unset): Exclude headers, navs, footers before markdown generation. Default: True.
        only_clean_content (bool | Unset): LLM pass to remove residual boilerplate from markdown. Default: False.
        max_concurrency (int | None | Unset): Maximum concurrent scrapes for this batch job.
        ignore_invalid_urls (bool | Unset): Skip invalid URLs instead of failing the whole batch. Default: True.
        wait_for (int | Unset): Extra delay in milliseconds before fetching page content. Default: 0.
        mobile (bool | Unset): Emulate a mobile device when scraping. Default: False.
        block_ads (bool | Unset): Enable ad-blocking and cookie-popup blocking. Default: True.
        remove_base_64_images (bool | Unset): Strip base64 image data from markdown output. Default: True.
        proxy (FirecrawlCrawlRequestProxyMode | Unset): Firecrawl proxy tier: `basic`, `enhanced`, or `auto`. Default:
            FirecrawlCrawlRequestProxyMode.AUTO.
        include_tags (list[str] | None | Unset): HTML tags to include in scrape output.
        exclude_tags (list[str] | None | Unset): HTML tags to exclude from scrape output.
        scrape_headers (FirecrawlCrawlRequestScrapeHeadersType0 | None | Unset): Headers sent to the target page
            (cookies, user-agent, etc.).
        max_age (int | None | Unset): Return cached page content younger than this age in milliseconds.
    """

    urls: list[str]
    crawler: Literal["Firecrawl"] | Unset = "Firecrawl"
    timeout: int | Unset = 30
    only_main_content: bool | Unset = True
    only_clean_content: bool | Unset = False
    max_concurrency: int | None | Unset = UNSET
    ignore_invalid_urls: bool | Unset = True
    wait_for: int | Unset = 0
    mobile: bool | Unset = False
    block_ads: bool | Unset = True
    remove_base_64_images: bool | Unset = True
    proxy: FirecrawlCrawlRequestProxyMode | Unset = FirecrawlCrawlRequestProxyMode.AUTO
    include_tags: list[str] | None | Unset = UNSET
    exclude_tags: list[str] | None | Unset = UNSET
    scrape_headers: FirecrawlCrawlRequestScrapeHeadersType0 | None | Unset = UNSET
    max_age: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.firecrawl_crawl_request_scrape_headers_type_0 import (
            FirecrawlCrawlRequestScrapeHeadersType0,
        )

        urls = self.urls

        crawler = self.crawler

        timeout = self.timeout

        only_main_content = self.only_main_content

        only_clean_content = self.only_clean_content

        max_concurrency: int | None | Unset
        if isinstance(self.max_concurrency, Unset):
            max_concurrency = UNSET
        else:
            max_concurrency = self.max_concurrency

        ignore_invalid_urls = self.ignore_invalid_urls

        wait_for = self.wait_for

        mobile = self.mobile

        block_ads = self.block_ads

        remove_base_64_images = self.remove_base_64_images

        proxy: str | Unset = UNSET
        if not isinstance(self.proxy, Unset):
            proxy = self.proxy.value

        include_tags: list[str] | None | Unset
        if isinstance(self.include_tags, Unset):
            include_tags = UNSET
        elif isinstance(self.include_tags, list):
            include_tags = self.include_tags

        else:
            include_tags = self.include_tags

        exclude_tags: list[str] | None | Unset
        if isinstance(self.exclude_tags, Unset):
            exclude_tags = UNSET
        elif isinstance(self.exclude_tags, list):
            exclude_tags = self.exclude_tags

        else:
            exclude_tags = self.exclude_tags

        scrape_headers: dict[str, Any] | None | Unset
        if isinstance(self.scrape_headers, Unset):
            scrape_headers = UNSET
        elif isinstance(self.scrape_headers, FirecrawlCrawlRequestScrapeHeadersType0):
            scrape_headers = self.scrape_headers.to_dict()
        else:
            scrape_headers = self.scrape_headers

        max_age: int | None | Unset
        if isinstance(self.max_age, Unset):
            max_age = UNSET
        else:
            max_age = self.max_age

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
        if only_main_content is not UNSET:
            field_dict["onlyMainContent"] = only_main_content
        if only_clean_content is not UNSET:
            field_dict["onlyCleanContent"] = only_clean_content
        if max_concurrency is not UNSET:
            field_dict["maxConcurrency"] = max_concurrency
        if ignore_invalid_urls is not UNSET:
            field_dict["ignoreInvalidUrls"] = ignore_invalid_urls
        if wait_for is not UNSET:
            field_dict["waitFor"] = wait_for
        if mobile is not UNSET:
            field_dict["mobile"] = mobile
        if block_ads is not UNSET:
            field_dict["blockAds"] = block_ads
        if remove_base_64_images is not UNSET:
            field_dict["removeBase64Images"] = remove_base_64_images
        if proxy is not UNSET:
            field_dict["proxy"] = proxy
        if include_tags is not UNSET:
            field_dict["includeTags"] = include_tags
        if exclude_tags is not UNSET:
            field_dict["excludeTags"] = exclude_tags
        if scrape_headers is not UNSET:
            field_dict["scrapeHeaders"] = scrape_headers
        if max_age is not UNSET:
            field_dict["maxAge"] = max_age

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.firecrawl_crawl_request_scrape_headers_type_0 import (
            FirecrawlCrawlRequestScrapeHeadersType0,
        )

        d = dict(src_dict)
        urls = cast(list[str], d.pop("urls"))

        crawler = cast(Literal["Firecrawl"] | Unset, d.pop("crawler", UNSET))
        if crawler != "Firecrawl" and not isinstance(crawler, Unset):
            raise ValueError(f"crawler must match const 'Firecrawl', got '{crawler}'")

        timeout = d.pop("timeout", UNSET)

        only_main_content = d.pop("onlyMainContent", UNSET)

        only_clean_content = d.pop("onlyCleanContent", UNSET)

        def _parse_max_concurrency(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        max_concurrency = _parse_max_concurrency(d.pop("maxConcurrency", UNSET))

        ignore_invalid_urls = d.pop("ignoreInvalidUrls", UNSET)

        wait_for = d.pop("waitFor", UNSET)

        mobile = d.pop("mobile", UNSET)

        block_ads = d.pop("blockAds", UNSET)

        remove_base_64_images = d.pop("removeBase64Images", UNSET)

        _proxy = d.pop("proxy", UNSET)
        proxy: FirecrawlCrawlRequestProxyMode | Unset
        if isinstance(_proxy, Unset):
            proxy = UNSET
        else:
            proxy = FirecrawlCrawlRequestProxyMode(_proxy)

        def _parse_include_tags(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                include_tags_type_0 = cast(list[str], data)

                return include_tags_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        include_tags = _parse_include_tags(d.pop("includeTags", UNSET))

        def _parse_exclude_tags(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                exclude_tags_type_0 = cast(list[str], data)

                return exclude_tags_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        exclude_tags = _parse_exclude_tags(d.pop("excludeTags", UNSET))

        def _parse_scrape_headers(
            data: object,
        ) -> FirecrawlCrawlRequestScrapeHeadersType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                scrape_headers_type_0 = (
                    FirecrawlCrawlRequestScrapeHeadersType0.from_dict(data)
                )

                return scrape_headers_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(FirecrawlCrawlRequestScrapeHeadersType0 | None | Unset, data)

        scrape_headers = _parse_scrape_headers(d.pop("scrapeHeaders", UNSET))

        def _parse_max_age(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        max_age = _parse_max_age(d.pop("maxAge", UNSET))

        firecrawl_crawl_request = cls(
            urls=urls,
            crawler=crawler,
            timeout=timeout,
            only_main_content=only_main_content,
            only_clean_content=only_clean_content,
            max_concurrency=max_concurrency,
            ignore_invalid_urls=ignore_invalid_urls,
            wait_for=wait_for,
            mobile=mobile,
            block_ads=block_ads,
            remove_base_64_images=remove_base_64_images,
            proxy=proxy,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            scrape_headers=scrape_headers,
            max_age=max_age,
        )

        firecrawl_crawl_request.additional_properties = d
        return firecrawl_crawl_request

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
