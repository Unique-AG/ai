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

from ..models.google_search_request_safe_search import GoogleSearchRequestSafeSearch
from ..models.google_search_request_site_search_filter_type_0 import (
    GoogleSearchRequestSiteSearchFilterType0,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="GoogleSearchRequest")


@_attrs_define
class GoogleSearchRequest:
    """
    Attributes:
        query (str): Search query string
        engine (Literal['google'] | Unset): Provider discriminator; must be `google` for this config. Default: 'google'.
        fetch_size (int | Unset): Default result count merged into each search request Default: 10.
        timeout (int | Unset): Request timeout in seconds Default: 30.
        search_engine_id (None | str | Unset): Google Programmable Search Engine ID (`cx`). Resolved from deployment env
            at runtime when not set. Not sent as a query parameter.
        safe (GoogleSearchRequestSafeSearch | Unset): SafeSearch level for every search: `active` (default) or `off`.
            Applied on all requests unless the call body overrides it. Default: GoogleSearchRequestSafeSearch.ACTIVE.
        gl (None | str | Unset): Two-letter ISO 3166-1 alpha-2 country code (Google `gl`).
        hl (None | str | Unset): Language for snippets and UI (Google `hl`).
        lr (None | str | Unset): Document language restrict (Google `lr`), e.g. `lang_en`.
        date_restrict (None | str | Unset): Recency filter (Google `dateRestrict`), e.g. `d7`, `m1`.
        exact_terms (None | str | Unset): Phrase every hit must contain (Google `exactTerms`).
        exclude_terms (None | str | Unset): Phrase that must not appear in results (Google `excludeTerms`).
        file_type (None | str | Unset): File extension filter (Google `fileType`), e.g. `pdf`.
        site_search (None | str | Unset): Site or domain to restrict results to (Google `siteSearch`).
        site_search_filter (GoogleSearchRequestSiteSearchFilterType0 | None | Unset): With `siteSearch`: `i` = include
            only that site, `e` = exclude it (Google `siteSearchFilter`).
        sort (None | str | Unset): Sort expression (Google `sort`), e.g. `date`.
    """

    query: str
    engine: Literal["google"] | Unset = "google"
    fetch_size: int | Unset = 10
    timeout: int | Unset = 30
    search_engine_id: None | str | Unset = UNSET
    safe: GoogleSearchRequestSafeSearch | Unset = GoogleSearchRequestSafeSearch.ACTIVE
    gl: None | str | Unset = UNSET
    hl: None | str | Unset = UNSET
    lr: None | str | Unset = UNSET
    date_restrict: None | str | Unset = UNSET
    exact_terms: None | str | Unset = UNSET
    exclude_terms: None | str | Unset = UNSET
    file_type: None | str | Unset = UNSET
    site_search: None | str | Unset = UNSET
    site_search_filter: GoogleSearchRequestSiteSearchFilterType0 | None | Unset = UNSET
    sort: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        engine = self.engine

        fetch_size = self.fetch_size

        timeout = self.timeout

        search_engine_id: None | str | Unset
        if isinstance(self.search_engine_id, Unset):
            search_engine_id = UNSET
        else:
            search_engine_id = self.search_engine_id

        safe: str | Unset = UNSET
        if not isinstance(self.safe, Unset):
            safe = self.safe.value

        gl: None | str | Unset
        if isinstance(self.gl, Unset):
            gl = UNSET
        else:
            gl = self.gl

        hl: None | str | Unset
        if isinstance(self.hl, Unset):
            hl = UNSET
        else:
            hl = self.hl

        lr: None | str | Unset
        if isinstance(self.lr, Unset):
            lr = UNSET
        else:
            lr = self.lr

        date_restrict: None | str | Unset
        if isinstance(self.date_restrict, Unset):
            date_restrict = UNSET
        else:
            date_restrict = self.date_restrict

        exact_terms: None | str | Unset
        if isinstance(self.exact_terms, Unset):
            exact_terms = UNSET
        else:
            exact_terms = self.exact_terms

        exclude_terms: None | str | Unset
        if isinstance(self.exclude_terms, Unset):
            exclude_terms = UNSET
        else:
            exclude_terms = self.exclude_terms

        file_type: None | str | Unset
        if isinstance(self.file_type, Unset):
            file_type = UNSET
        else:
            file_type = self.file_type

        site_search: None | str | Unset
        if isinstance(self.site_search, Unset):
            site_search = UNSET
        else:
            site_search = self.site_search

        site_search_filter: None | str | Unset
        if isinstance(self.site_search_filter, Unset):
            site_search_filter = UNSET
        elif isinstance(
            self.site_search_filter, GoogleSearchRequestSiteSearchFilterType0
        ):
            site_search_filter = self.site_search_filter.value
        else:
            site_search_filter = self.site_search_filter

        sort: None | str | Unset
        if isinstance(self.sort, Unset):
            sort = UNSET
        else:
            sort = self.sort

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
        if search_engine_id is not UNSET:
            field_dict["searchEngineId"] = search_engine_id
        if safe is not UNSET:
            field_dict["safe"] = safe
        if gl is not UNSET:
            field_dict["gl"] = gl
        if hl is not UNSET:
            field_dict["hl"] = hl
        if lr is not UNSET:
            field_dict["lr"] = lr
        if date_restrict is not UNSET:
            field_dict["dateRestrict"] = date_restrict
        if exact_terms is not UNSET:
            field_dict["exactTerms"] = exact_terms
        if exclude_terms is not UNSET:
            field_dict["excludeTerms"] = exclude_terms
        if file_type is not UNSET:
            field_dict["fileType"] = file_type
        if site_search is not UNSET:
            field_dict["siteSearch"] = site_search
        if site_search_filter is not UNSET:
            field_dict["siteSearchFilter"] = site_search_filter
        if sort is not UNSET:
            field_dict["sort"] = sort

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        engine = cast(Literal["google"] | Unset, d.pop("engine", UNSET))
        if engine != "google" and not isinstance(engine, Unset):
            raise ValueError(f"engine must match const 'google', got '{engine}'")

        fetch_size = d.pop("fetchSize", UNSET)

        timeout = d.pop("timeout", UNSET)

        def _parse_search_engine_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        search_engine_id = _parse_search_engine_id(d.pop("searchEngineId", UNSET))

        _safe = d.pop("safe", UNSET)
        safe: GoogleSearchRequestSafeSearch | Unset
        if isinstance(_safe, Unset):
            safe = UNSET
        else:
            safe = GoogleSearchRequestSafeSearch(_safe)

        def _parse_gl(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        gl = _parse_gl(d.pop("gl", UNSET))

        def _parse_hl(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        hl = _parse_hl(d.pop("hl", UNSET))

        def _parse_lr(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        lr = _parse_lr(d.pop("lr", UNSET))

        def _parse_date_restrict(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        date_restrict = _parse_date_restrict(d.pop("dateRestrict", UNSET))

        def _parse_exact_terms(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        exact_terms = _parse_exact_terms(d.pop("exactTerms", UNSET))

        def _parse_exclude_terms(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        exclude_terms = _parse_exclude_terms(d.pop("excludeTerms", UNSET))

        def _parse_file_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        file_type = _parse_file_type(d.pop("fileType", UNSET))

        def _parse_site_search(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        site_search = _parse_site_search(d.pop("siteSearch", UNSET))

        def _parse_site_search_filter(
            data: object,
        ) -> GoogleSearchRequestSiteSearchFilterType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                site_search_filter_type_0 = GoogleSearchRequestSiteSearchFilterType0(
                    data
                )

                return site_search_filter_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(GoogleSearchRequestSiteSearchFilterType0 | None | Unset, data)

        site_search_filter = _parse_site_search_filter(d.pop("siteSearchFilter", UNSET))

        def _parse_sort(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        sort = _parse_sort(d.pop("sort", UNSET))

        google_search_request = cls(
            query=query,
            engine=engine,
            fetch_size=fetch_size,
            timeout=timeout,
            search_engine_id=search_engine_id,
            safe=safe,
            gl=gl,
            hl=hl,
            lr=lr,
            date_restrict=date_restrict,
            exact_terms=exact_terms,
            exclude_terms=exclude_terms,
            file_type=file_type,
            site_search=site_search,
            site_search_filter=site_search_filter,
            sort=sort,
        )

        google_search_request.additional_properties = d
        return google_search_request

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
