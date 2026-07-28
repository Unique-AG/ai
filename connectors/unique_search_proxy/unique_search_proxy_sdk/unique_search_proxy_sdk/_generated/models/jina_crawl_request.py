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

from ..models.jina_crawl_request_engine import JinaCrawlRequestEngine
from ..models.jina_crawl_request_retain_images_type_0 import (
    JinaCrawlRequestRetainImagesType0,
)
from ..models.jina_crawl_request_return_format import JinaCrawlRequestReturnFormat
from ..types import UNSET, Unset

T = TypeVar("T", bound="JinaCrawlRequest")


@_attrs_define
class JinaCrawlRequest:
    """
    Attributes:
        urls (list[str]): URLs to crawl
        crawler (Literal['Jina'] | Unset): Provider discriminator; must be `Jina` for this config. Default: 'Jina'.
        timeout (int | Unset): Request timeout in seconds Default: 30.
        return_format (JinaCrawlRequestReturnFormat | Unset): Jina Reader output format: `markdown`, `html`, `text`,
            `screenshot`, or `pageshot`. Default: JinaCrawlRequestReturnFormat.MARKDOWN.
        engine (JinaCrawlRequestEngine | Unset): `browser` for best quality, `direct` for speed, `cf-browser-rendering`
            for JS-heavy sites. Default: JinaCrawlRequestEngine.BROWSER.
        page_timeout (int | None | Unset): Max seconds to wait for the page to load (Jina Reader). Defaults to the crawl
            `timeout` when unset.
        max_concurrent_requests (int | Unset): Maximum concurrent Jina Reader POST requests. Default: 10.
        no_cache (bool | Unset): Bypass Jina cache and fetch fresh content. Default: False.
        target_selector (list[str] | None | Unset): CSS selectors to focus extraction on specific page elements.
        wait_for_selector (list[str] | None | Unset): CSS selectors to wait for before returning content.
        remove_selector (list[str] | None | Unset): CSS selectors for page regions to strip (headers, footers, etc.).
        with_generated_alt (bool | Unset): Generate alt text for images missing alt tags. Default: False.
        with_links_summary (bool | Unset): Include a links summary in the reader response. Default: False.
        with_images_summary (bool | Unset): Include an images summary in the reader response. Default: False.
        with_iframe (bool | Unset): Include iframe content in the reader response. Default: False.
        retain_images (JinaCrawlRequestRetainImagesType0 | None | Unset): Control which images are retained in markdown
            output.
        locale (None | str | Unset): Browser locale used to render the page (e.g. `en-US`).
        referer (None | str | Unset): Referer header sent when fetching the target URL.
        proxy_url (None | str | Unset): Proxy URL used by Jina Reader to access the target page.
        do_not_track (bool | Unset): Send DNT (Do Not Track) to the reader service. Default: True.
    """

    urls: list[str]
    crawler: Literal["Jina"] | Unset = "Jina"
    timeout: int | Unset = 30
    return_format: JinaCrawlRequestReturnFormat | Unset = (
        JinaCrawlRequestReturnFormat.MARKDOWN
    )
    engine: JinaCrawlRequestEngine | Unset = JinaCrawlRequestEngine.BROWSER
    page_timeout: int | None | Unset = UNSET
    max_concurrent_requests: int | Unset = 10
    no_cache: bool | Unset = False
    target_selector: list[str] | None | Unset = UNSET
    wait_for_selector: list[str] | None | Unset = UNSET
    remove_selector: list[str] | None | Unset = UNSET
    with_generated_alt: bool | Unset = False
    with_links_summary: bool | Unset = False
    with_images_summary: bool | Unset = False
    with_iframe: bool | Unset = False
    retain_images: JinaCrawlRequestRetainImagesType0 | None | Unset = UNSET
    locale: None | str | Unset = UNSET
    referer: None | str | Unset = UNSET
    proxy_url: None | str | Unset = UNSET
    do_not_track: bool | Unset = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        urls = self.urls

        crawler = self.crawler

        timeout = self.timeout

        return_format: str | Unset = UNSET
        if not isinstance(self.return_format, Unset):
            return_format = self.return_format.value

        engine: str | Unset = UNSET
        if not isinstance(self.engine, Unset):
            engine = self.engine.value

        page_timeout: int | None | Unset
        if isinstance(self.page_timeout, Unset):
            page_timeout = UNSET
        else:
            page_timeout = self.page_timeout

        max_concurrent_requests = self.max_concurrent_requests

        no_cache = self.no_cache

        target_selector: list[str] | None | Unset
        if isinstance(self.target_selector, Unset):
            target_selector = UNSET
        elif isinstance(self.target_selector, list):
            target_selector = self.target_selector

        else:
            target_selector = self.target_selector

        wait_for_selector: list[str] | None | Unset
        if isinstance(self.wait_for_selector, Unset):
            wait_for_selector = UNSET
        elif isinstance(self.wait_for_selector, list):
            wait_for_selector = self.wait_for_selector

        else:
            wait_for_selector = self.wait_for_selector

        remove_selector: list[str] | None | Unset
        if isinstance(self.remove_selector, Unset):
            remove_selector = UNSET
        elif isinstance(self.remove_selector, list):
            remove_selector = self.remove_selector

        else:
            remove_selector = self.remove_selector

        with_generated_alt = self.with_generated_alt

        with_links_summary = self.with_links_summary

        with_images_summary = self.with_images_summary

        with_iframe = self.with_iframe

        retain_images: None | str | Unset
        if isinstance(self.retain_images, Unset):
            retain_images = UNSET
        elif isinstance(self.retain_images, JinaCrawlRequestRetainImagesType0):
            retain_images = self.retain_images.value
        else:
            retain_images = self.retain_images

        locale: None | str | Unset
        if isinstance(self.locale, Unset):
            locale = UNSET
        else:
            locale = self.locale

        referer: None | str | Unset
        if isinstance(self.referer, Unset):
            referer = UNSET
        else:
            referer = self.referer

        proxy_url: None | str | Unset
        if isinstance(self.proxy_url, Unset):
            proxy_url = UNSET
        else:
            proxy_url = self.proxy_url

        do_not_track = self.do_not_track

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
        if return_format is not UNSET:
            field_dict["returnFormat"] = return_format
        if engine is not UNSET:
            field_dict["engine"] = engine
        if page_timeout is not UNSET:
            field_dict["pageTimeout"] = page_timeout
        if max_concurrent_requests is not UNSET:
            field_dict["maxConcurrentRequests"] = max_concurrent_requests
        if no_cache is not UNSET:
            field_dict["noCache"] = no_cache
        if target_selector is not UNSET:
            field_dict["targetSelector"] = target_selector
        if wait_for_selector is not UNSET:
            field_dict["waitForSelector"] = wait_for_selector
        if remove_selector is not UNSET:
            field_dict["removeSelector"] = remove_selector
        if with_generated_alt is not UNSET:
            field_dict["withGeneratedAlt"] = with_generated_alt
        if with_links_summary is not UNSET:
            field_dict["withLinksSummary"] = with_links_summary
        if with_images_summary is not UNSET:
            field_dict["withImagesSummary"] = with_images_summary
        if with_iframe is not UNSET:
            field_dict["withIframe"] = with_iframe
        if retain_images is not UNSET:
            field_dict["retainImages"] = retain_images
        if locale is not UNSET:
            field_dict["locale"] = locale
        if referer is not UNSET:
            field_dict["referer"] = referer
        if proxy_url is not UNSET:
            field_dict["proxyUrl"] = proxy_url
        if do_not_track is not UNSET:
            field_dict["doNotTrack"] = do_not_track

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        urls = cast(list[str], d.pop("urls"))

        crawler = cast(Literal["Jina"] | Unset, d.pop("crawler", UNSET))
        if crawler != "Jina" and not isinstance(crawler, Unset):
            raise ValueError(f"crawler must match const 'Jina', got '{crawler}'")

        timeout = d.pop("timeout", UNSET)

        _return_format = d.pop("returnFormat", UNSET)
        return_format: JinaCrawlRequestReturnFormat | Unset
        if isinstance(_return_format, Unset):
            return_format = UNSET
        else:
            return_format = JinaCrawlRequestReturnFormat(_return_format)

        _engine = d.pop("engine", UNSET)
        engine: JinaCrawlRequestEngine | Unset
        if isinstance(_engine, Unset):
            engine = UNSET
        else:
            engine = JinaCrawlRequestEngine(_engine)

        def _parse_page_timeout(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        page_timeout = _parse_page_timeout(d.pop("pageTimeout", UNSET))

        max_concurrent_requests = d.pop("maxConcurrentRequests", UNSET)

        no_cache = d.pop("noCache", UNSET)

        def _parse_target_selector(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                target_selector_type_0 = cast(list[str], data)

                return target_selector_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        target_selector = _parse_target_selector(d.pop("targetSelector", UNSET))

        def _parse_wait_for_selector(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                wait_for_selector_type_0 = cast(list[str], data)

                return wait_for_selector_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        wait_for_selector = _parse_wait_for_selector(d.pop("waitForSelector", UNSET))

        def _parse_remove_selector(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                remove_selector_type_0 = cast(list[str], data)

                return remove_selector_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        remove_selector = _parse_remove_selector(d.pop("removeSelector", UNSET))

        with_generated_alt = d.pop("withGeneratedAlt", UNSET)

        with_links_summary = d.pop("withLinksSummary", UNSET)

        with_images_summary = d.pop("withImagesSummary", UNSET)

        with_iframe = d.pop("withIframe", UNSET)

        def _parse_retain_images(
            data: object,
        ) -> JinaCrawlRequestRetainImagesType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                retain_images_type_0 = JinaCrawlRequestRetainImagesType0(data)

                return retain_images_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(JinaCrawlRequestRetainImagesType0 | None | Unset, data)

        retain_images = _parse_retain_images(d.pop("retainImages", UNSET))

        def _parse_locale(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        locale = _parse_locale(d.pop("locale", UNSET))

        def _parse_referer(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        referer = _parse_referer(d.pop("referer", UNSET))

        def _parse_proxy_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        proxy_url = _parse_proxy_url(d.pop("proxyUrl", UNSET))

        do_not_track = d.pop("doNotTrack", UNSET)

        jina_crawl_request = cls(
            urls=urls,
            crawler=crawler,
            timeout=timeout,
            return_format=return_format,
            engine=engine,
            page_timeout=page_timeout,
            max_concurrent_requests=max_concurrent_requests,
            no_cache=no_cache,
            target_selector=target_selector,
            wait_for_selector=wait_for_selector,
            remove_selector=remove_selector,
            with_generated_alt=with_generated_alt,
            with_links_summary=with_links_summary,
            with_images_summary=with_images_summary,
            with_iframe=with_iframe,
            retain_images=retain_images,
            locale=locale,
            referer=referer,
            proxy_url=proxy_url,
            do_not_track=do_not_track,
        )

        jina_crawl_request.additional_properties = d
        return jina_crawl_request

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
