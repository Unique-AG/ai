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

from ..models.perplexity_search_request_search_context_size import (
    PerplexitySearchRequestSearchContextSize,
)
from ..models.perplexity_search_request_search_recency_filter_type_0 import (
    PerplexitySearchRequestSearchRecencyFilterType0,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="PerplexitySearchRequest")


@_attrs_define
class PerplexitySearchRequest:
    """
    Attributes:
        query (str): Search query string
        engine (Literal['perplexity'] | Unset): Provider discriminator; must be `perplexity` for this config. Default:
            'perplexity'.
        fetch_size (int | Unset): Default result count merged into each search request Default: 10.
        timeout (int | Unset): Request timeout in seconds Default: 30.
        max_tokens (int | None | Unset): Maximum total webpage content tokens across all results (Perplexity
            `max_tokens`). Omitted when unset. Omit `search_context_size` when using this or `max_tokens_per_page`.
        max_tokens_per_page (int | None | Unset): Maximum webpage content tokens extracted from each result page
            (Perplexity `max_tokens_per_page`). Omitted when unset. Omit `search_context_size` when using this or
            `max_tokens`.
        search_context_size (PerplexitySearchRequestSearchContextSize | Unset): How much content is extracted from
            result pages (Perplexity `search_context_size`): `low`, `medium`, or `high` (API default). Omit when using
            `max_tokens` or `max_tokens_per_page`. Default: PerplexitySearchRequestSearchContextSize.MEDIUM.
        country (None | str | Unset): ISO 3166-1 alpha-2 country code (Perplexity `country`, two letters).
        search_language_filter (list[str] | None | Unset): ISO 639-1 language codes to include (Perplexity
            `search_language_filter`; two characters each, up to 20).
        search_domain_filter (list[str] | None | Unset): Domains to limit results to (Perplexity `search_domain_filter`;
            up to 20).
        search_recency_filter (None | PerplexitySearchRequestSearchRecencyFilterType0 | Unset): Publication recency
            filter (Perplexity `search_recency_filter`): `hour`, `day`, `week`, `month`, or `year`.
        last_updated_after_filter (None | str | Unset): Return results updated after this date (Perplexity
            `last_updated_after_filter`; format `MM/DD/YYYY`).
        last_updated_before_filter (None | str | Unset): Return results updated before this date (Perplexity
            `last_updated_before_filter`; format `MM/DD/YYYY`).
        search_after_date_filter (None | str | Unset): Return results published after this date (Perplexity
            `search_after_date_filter`; format `MM/DD/YYYY`).
        search_before_date_filter (None | str | Unset): Return results published before this date (Perplexity
            `search_before_date_filter`; format `MM/DD/YYYY`).
    """

    query: str
    engine: Literal["perplexity"] | Unset = "perplexity"
    fetch_size: int | Unset = 10
    timeout: int | Unset = 30
    max_tokens: int | None | Unset = UNSET
    max_tokens_per_page: int | None | Unset = UNSET
    search_context_size: PerplexitySearchRequestSearchContextSize | Unset = (
        PerplexitySearchRequestSearchContextSize.MEDIUM
    )
    country: None | str | Unset = UNSET
    search_language_filter: list[str] | None | Unset = UNSET
    search_domain_filter: list[str] | None | Unset = UNSET
    search_recency_filter: (
        None | PerplexitySearchRequestSearchRecencyFilterType0 | Unset
    ) = UNSET
    last_updated_after_filter: None | str | Unset = UNSET
    last_updated_before_filter: None | str | Unset = UNSET
    search_after_date_filter: None | str | Unset = UNSET
    search_before_date_filter: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        engine = self.engine

        fetch_size = self.fetch_size

        timeout = self.timeout

        max_tokens: int | None | Unset
        if isinstance(self.max_tokens, Unset):
            max_tokens = UNSET
        else:
            max_tokens = self.max_tokens

        max_tokens_per_page: int | None | Unset
        if isinstance(self.max_tokens_per_page, Unset):
            max_tokens_per_page = UNSET
        else:
            max_tokens_per_page = self.max_tokens_per_page

        search_context_size: str | Unset = UNSET
        if not isinstance(self.search_context_size, Unset):
            search_context_size = self.search_context_size.value

        country: None | str | Unset
        if isinstance(self.country, Unset):
            country = UNSET
        else:
            country = self.country

        search_language_filter: list[str] | None | Unset
        if isinstance(self.search_language_filter, Unset):
            search_language_filter = UNSET
        elif isinstance(self.search_language_filter, list):
            search_language_filter = self.search_language_filter

        else:
            search_language_filter = self.search_language_filter

        search_domain_filter: list[str] | None | Unset
        if isinstance(self.search_domain_filter, Unset):
            search_domain_filter = UNSET
        elif isinstance(self.search_domain_filter, list):
            search_domain_filter = self.search_domain_filter

        else:
            search_domain_filter = self.search_domain_filter

        search_recency_filter: None | str | Unset
        if isinstance(self.search_recency_filter, Unset):
            search_recency_filter = UNSET
        elif isinstance(
            self.search_recency_filter, PerplexitySearchRequestSearchRecencyFilterType0
        ):
            search_recency_filter = self.search_recency_filter.value
        else:
            search_recency_filter = self.search_recency_filter

        last_updated_after_filter: None | str | Unset
        if isinstance(self.last_updated_after_filter, Unset):
            last_updated_after_filter = UNSET
        else:
            last_updated_after_filter = self.last_updated_after_filter

        last_updated_before_filter: None | str | Unset
        if isinstance(self.last_updated_before_filter, Unset):
            last_updated_before_filter = UNSET
        else:
            last_updated_before_filter = self.last_updated_before_filter

        search_after_date_filter: None | str | Unset
        if isinstance(self.search_after_date_filter, Unset):
            search_after_date_filter = UNSET
        else:
            search_after_date_filter = self.search_after_date_filter

        search_before_date_filter: None | str | Unset
        if isinstance(self.search_before_date_filter, Unset):
            search_before_date_filter = UNSET
        else:
            search_before_date_filter = self.search_before_date_filter

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
        if max_tokens is not UNSET:
            field_dict["maxTokens"] = max_tokens
        if max_tokens_per_page is not UNSET:
            field_dict["maxTokensPerPage"] = max_tokens_per_page
        if search_context_size is not UNSET:
            field_dict["searchContextSize"] = search_context_size
        if country is not UNSET:
            field_dict["country"] = country
        if search_language_filter is not UNSET:
            field_dict["searchLanguageFilter"] = search_language_filter
        if search_domain_filter is not UNSET:
            field_dict["searchDomainFilter"] = search_domain_filter
        if search_recency_filter is not UNSET:
            field_dict["searchRecencyFilter"] = search_recency_filter
        if last_updated_after_filter is not UNSET:
            field_dict["lastUpdatedAfterFilter"] = last_updated_after_filter
        if last_updated_before_filter is not UNSET:
            field_dict["lastUpdatedBeforeFilter"] = last_updated_before_filter
        if search_after_date_filter is not UNSET:
            field_dict["searchAfterDateFilter"] = search_after_date_filter
        if search_before_date_filter is not UNSET:
            field_dict["searchBeforeDateFilter"] = search_before_date_filter

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        engine = cast(Literal["perplexity"] | Unset, d.pop("engine", UNSET))
        if engine != "perplexity" and not isinstance(engine, Unset):
            raise ValueError(f"engine must match const 'perplexity', got '{engine}'")

        fetch_size = d.pop("fetchSize", UNSET)

        timeout = d.pop("timeout", UNSET)

        def _parse_max_tokens(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        max_tokens = _parse_max_tokens(d.pop("maxTokens", UNSET))

        def _parse_max_tokens_per_page(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        max_tokens_per_page = _parse_max_tokens_per_page(
            d.pop("maxTokensPerPage", UNSET)
        )

        _search_context_size = d.pop("searchContextSize", UNSET)
        search_context_size: PerplexitySearchRequestSearchContextSize | Unset
        if isinstance(_search_context_size, Unset):
            search_context_size = UNSET
        else:
            search_context_size = PerplexitySearchRequestSearchContextSize(
                _search_context_size
            )

        def _parse_country(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        country = _parse_country(d.pop("country", UNSET))

        def _parse_search_language_filter(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                search_language_filter_type_0 = cast(list[str], data)

                return search_language_filter_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        search_language_filter = _parse_search_language_filter(
            d.pop("searchLanguageFilter", UNSET)
        )

        def _parse_search_domain_filter(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                search_domain_filter_type_0 = cast(list[str], data)

                return search_domain_filter_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        search_domain_filter = _parse_search_domain_filter(
            d.pop("searchDomainFilter", UNSET)
        )

        def _parse_search_recency_filter(
            data: object,
        ) -> None | PerplexitySearchRequestSearchRecencyFilterType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                search_recency_filter_type_0 = (
                    PerplexitySearchRequestSearchRecencyFilterType0(data)
                )

                return search_recency_filter_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                None | PerplexitySearchRequestSearchRecencyFilterType0 | Unset, data
            )

        search_recency_filter = _parse_search_recency_filter(
            d.pop("searchRecencyFilter", UNSET)
        )

        def _parse_last_updated_after_filter(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_updated_after_filter = _parse_last_updated_after_filter(
            d.pop("lastUpdatedAfterFilter", UNSET)
        )

        def _parse_last_updated_before_filter(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last_updated_before_filter = _parse_last_updated_before_filter(
            d.pop("lastUpdatedBeforeFilter", UNSET)
        )

        def _parse_search_after_date_filter(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        search_after_date_filter = _parse_search_after_date_filter(
            d.pop("searchAfterDateFilter", UNSET)
        )

        def _parse_search_before_date_filter(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        search_before_date_filter = _parse_search_before_date_filter(
            d.pop("searchBeforeDateFilter", UNSET)
        )

        perplexity_search_request = cls(
            query=query,
            engine=engine,
            fetch_size=fetch_size,
            timeout=timeout,
            max_tokens=max_tokens,
            max_tokens_per_page=max_tokens_per_page,
            search_context_size=search_context_size,
            country=country,
            search_language_filter=search_language_filter,
            search_domain_filter=search_domain_filter,
            search_recency_filter=search_recency_filter,
            last_updated_after_filter=last_updated_after_filter,
            last_updated_before_filter=last_updated_before_filter,
            search_after_date_filter=search_after_date_filter,
            search_before_date_filter=search_before_date_filter,
        )

        perplexity_search_request.additional_properties = d
        return perplexity_search_request

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
