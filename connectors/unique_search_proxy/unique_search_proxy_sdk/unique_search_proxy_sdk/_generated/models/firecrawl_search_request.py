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

from ..models.firecrawl_search_request_category_type_0 import (
    FirecrawlSearchRequestCategoryType0,
)
from ..models.firecrawl_search_request_sources import FirecrawlSearchRequestSources
from ..models.firecrawl_search_request_time_filter_type_0 import (
    FirecrawlSearchRequestTimeFilterType0,
)
from ..models.firecrawl_search_request_zero_data_retention import (
    FirecrawlSearchRequestZeroDataRetention,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="FirecrawlSearchRequest")


@_attrs_define
class FirecrawlSearchRequest:
    """
    Attributes:
        query (str): Search query string
        engine (Literal['firecrawl'] | Unset): Provider discriminator; must be `firecrawl` for this config. Default:
            'firecrawl'.
        fetch_size (int | Unset): Number of results per search, web and news together. Firecrawl bills every started
            block of 10 results: 2 credits, or 10 credits with end-to-end zero data retention (`zdr`). So 11 results cost
            twice as much as 10. Default: 10.
        timeout (int | Unset): Request timeout in seconds Default: 30.
        sources (FirecrawlSearchRequestSources | Unset): Web searches regular web pages, News searches news articles.
            Web and news searches both: each source returns the full result count, so up to twice the results and the cost.
            The time filter does not apply to news. Default: FirecrawlSearchRequestSources.WEB.
        highlights (bool | Unset): Firecrawl replaces each result's preview with the passages of the page that match the
            query, which can be a whole table. Off returns the website's short description. Searches with zero data
            retention always return the short description. Default: True.
        safe_search (bool | Unset): Filter explicit content from the results. Default: False.
        sort_by_date (bool | Unset): Return the newest web results first instead of the best matches. Default: False.
        zero_data_retention (FirecrawlSearchRequestZeroDataRetention | Unset): Raise zero data retention for this
            configuration above what the Search Proxy is deployed with. It can never lower it. `anon` costs 2 credits per 10
            results, `zdr` 10. Firecrawl must have enabled the mode for the account, otherwise every search fails. Default:
            FirecrawlSearchRequestZeroDataRetention.DEPLOYMENT.
        exclude_domains (list[str] | None | Unset): Never return results from these hostnames, for example
            `example.com`. Not exposed to the model.
        time_filter (FirecrawlSearchRequestTimeFilterType0 | None | Unset): Only return web results from the past hour
            (`qdr:h`), day (`qdr:d`), week (`qdr:w`), month (`qdr:m`) or year (`qdr:y`). Does not filter news results.
        country (None | str | Unset): ISO 3166-1 alpha-2 country code that results are localised for, for example `CH`.
            Unset uses Firecrawl's default, `US`.
        location (None | str | Unset): Location that results are localised for, for example `Zurich,Switzerland`. Set
            together with the country.
        include_domains (list[str] | None | Unset): Only return results from these hostnames, for example `snb.ch`.
            Excluded domains are removed from this list.
        category (FirecrawlSearchRequestCategoryType0 | None | Unset): Only return one kind of web result: `research`
            (academic and research sites), `pdf` (PDF documents), `gov` (government publications, which cost no search
            credits) or `developer` (developer sites).
    """

    query: str
    engine: Literal["firecrawl"] | Unset = "firecrawl"
    fetch_size: int | Unset = 10
    timeout: int | Unset = 30
    sources: FirecrawlSearchRequestSources | Unset = FirecrawlSearchRequestSources.WEB
    highlights: bool | Unset = True
    safe_search: bool | Unset = False
    sort_by_date: bool | Unset = False
    zero_data_retention: FirecrawlSearchRequestZeroDataRetention | Unset = (
        FirecrawlSearchRequestZeroDataRetention.DEPLOYMENT
    )
    exclude_domains: list[str] | None | Unset = UNSET
    time_filter: FirecrawlSearchRequestTimeFilterType0 | None | Unset = UNSET
    country: None | str | Unset = UNSET
    location: None | str | Unset = UNSET
    include_domains: list[str] | None | Unset = UNSET
    category: FirecrawlSearchRequestCategoryType0 | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        engine = self.engine

        fetch_size = self.fetch_size

        timeout = self.timeout

        sources: str | Unset = UNSET
        if not isinstance(self.sources, Unset):
            sources = self.sources.value

        highlights = self.highlights

        safe_search = self.safe_search

        sort_by_date = self.sort_by_date

        zero_data_retention: str | Unset = UNSET
        if not isinstance(self.zero_data_retention, Unset):
            zero_data_retention = self.zero_data_retention.value

        exclude_domains: list[str] | None | Unset
        if isinstance(self.exclude_domains, Unset):
            exclude_domains = UNSET
        elif isinstance(self.exclude_domains, list):
            exclude_domains = self.exclude_domains

        else:
            exclude_domains = self.exclude_domains

        time_filter: None | str | Unset
        if isinstance(self.time_filter, Unset):
            time_filter = UNSET
        elif isinstance(self.time_filter, FirecrawlSearchRequestTimeFilterType0):
            time_filter = self.time_filter.value
        else:
            time_filter = self.time_filter

        country: None | str | Unset
        if isinstance(self.country, Unset):
            country = UNSET
        else:
            country = self.country

        location: None | str | Unset
        if isinstance(self.location, Unset):
            location = UNSET
        else:
            location = self.location

        include_domains: list[str] | None | Unset
        if isinstance(self.include_domains, Unset):
            include_domains = UNSET
        elif isinstance(self.include_domains, list):
            include_domains = self.include_domains

        else:
            include_domains = self.include_domains

        category: None | str | Unset
        if isinstance(self.category, Unset):
            category = UNSET
        elif isinstance(self.category, FirecrawlSearchRequestCategoryType0):
            category = self.category.value
        else:
            category = self.category

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
        if sources is not UNSET:
            field_dict["sources"] = sources
        if highlights is not UNSET:
            field_dict["highlights"] = highlights
        if safe_search is not UNSET:
            field_dict["safeSearch"] = safe_search
        if sort_by_date is not UNSET:
            field_dict["sortByDate"] = sort_by_date
        if zero_data_retention is not UNSET:
            field_dict["zeroDataRetention"] = zero_data_retention
        if exclude_domains is not UNSET:
            field_dict["excludeDomains"] = exclude_domains
        if time_filter is not UNSET:
            field_dict["timeFilter"] = time_filter
        if country is not UNSET:
            field_dict["country"] = country
        if location is not UNSET:
            field_dict["location"] = location
        if include_domains is not UNSET:
            field_dict["includeDomains"] = include_domains
        if category is not UNSET:
            field_dict["category"] = category

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        engine = cast(Literal["firecrawl"] | Unset, d.pop("engine", UNSET))
        if engine != "firecrawl" and not isinstance(engine, Unset):
            raise ValueError(f"engine must match const 'firecrawl', got '{engine}'")

        fetch_size = d.pop("fetchSize", UNSET)

        timeout = d.pop("timeout", UNSET)

        _sources = d.pop("sources", UNSET)
        sources: FirecrawlSearchRequestSources | Unset
        if isinstance(_sources, Unset):
            sources = UNSET
        else:
            sources = FirecrawlSearchRequestSources(_sources)

        highlights = d.pop("highlights", UNSET)

        safe_search = d.pop("safeSearch", UNSET)

        sort_by_date = d.pop("sortByDate", UNSET)

        _zero_data_retention = d.pop("zeroDataRetention", UNSET)
        zero_data_retention: FirecrawlSearchRequestZeroDataRetention | Unset
        if isinstance(_zero_data_retention, Unset):
            zero_data_retention = UNSET
        else:
            zero_data_retention = FirecrawlSearchRequestZeroDataRetention(
                _zero_data_retention
            )

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

        def _parse_time_filter(
            data: object,
        ) -> FirecrawlSearchRequestTimeFilterType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                time_filter_type_0 = FirecrawlSearchRequestTimeFilterType0(data)

                return time_filter_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(FirecrawlSearchRequestTimeFilterType0 | None | Unset, data)

        time_filter = _parse_time_filter(d.pop("timeFilter", UNSET))

        def _parse_country(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        country = _parse_country(d.pop("country", UNSET))

        def _parse_location(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        location = _parse_location(d.pop("location", UNSET))

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

        def _parse_category(
            data: object,
        ) -> FirecrawlSearchRequestCategoryType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                category_type_0 = FirecrawlSearchRequestCategoryType0(data)

                return category_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(FirecrawlSearchRequestCategoryType0 | None | Unset, data)

        category = _parse_category(d.pop("category", UNSET))

        firecrawl_search_request = cls(
            query=query,
            engine=engine,
            fetch_size=fetch_size,
            timeout=timeout,
            sources=sources,
            highlights=highlights,
            safe_search=safe_search,
            sort_by_date=sort_by_date,
            zero_data_retention=zero_data_retention,
            exclude_domains=exclude_domains,
            time_filter=time_filter,
            country=country,
            location=location,
            include_domains=include_domains,
            category=category,
        )

        firecrawl_search_request.additional_properties = d
        return firecrawl_search_request

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
