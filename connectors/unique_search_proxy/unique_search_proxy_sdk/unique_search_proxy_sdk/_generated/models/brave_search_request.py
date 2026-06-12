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

from ..models.brave_search_request_safesearch_type_0 import (
    BraveSearchRequestSafesearchType0,
)
from ..models.brave_search_request_units_type_0 import BraveSearchRequestUnitsType0
from ..types import UNSET, Unset

T = TypeVar("T", bound="BraveSearchRequest")


@_attrs_define
class BraveSearchRequest:
    """
    Attributes:
        query (str): Search query string
        engine (Literal['brave'] | Unset): Provider discriminator; must be `brave` for this config. Default: 'brave'.
        fetch_size (int | Unset): Default result count merged into each search request Default: 10.
        timeout (int | Unset): Request timeout in seconds Default: 30.
        extra_snippets (bool | Unset): Request up to five additional alternative excerpts per result (Brave
            `extra_snippets`). Default: True.
        spellcheck (bool | Unset): Whether Brave spell-checks the query and uses the corrected form. Default: False.
        text_decorations (bool | Unset): Whether result snippets include decoration markers (e.g. highlighting).
            Default: True.
        operators (bool | Unset): Whether Brave applies search operators in the query. Default: True.
        ui_lang (str | Unset): User interface language for response strings (Brave `ui_lang`), e.g. `en-US`. Distinct
            from `search_lang`. Default: 'en-US'.
        units (BraveSearchRequestUnitsType0 | None | Unset): Measurement units for location-rich results: `metric` or
            `imperial`.
        summary (bool | Unset): Enable summary key generation in web search results (Brave summarizer). Default: True.
        include_fetch_metadata (bool | Unset): Include fetch metadata in the Brave response. Default: False.
        goggles (list[str] | str | Unset): Custom re-ranking Goggle URL(s) or definition(s). Up to three Goggles per
            request.
        country (None | str | Unset): Two-letter ISO 3166-1 alpha-2 country code for result origin (Brave `country`).
            Set `value` for a fixed default; set `expose` so the LLM may override per query.
        freshness (None | str | Unset): Recency filter: `pd`, `pw`, `pm`, `py`, or `YYYY-MM-DDtoYYYY-MM-DD`. `value` +
            `expose` behave like `country`.
        search_lang (None | str | Unset): Language code for result documents (Brave `search_lang`). `value` + `expose`
            behave like `country`.
        safesearch (BraveSearchRequestSafesearchType0 | None | Unset): Adult content filter: `off`, `moderate` (API
            default), or `strict`. Usually set via admin `value`; enable `expose` only if the LLM may tune per query.
        result_filter (list[str] | None | Unset): Result types to include, e.g. `web`, `news`, `videos`. Omit (`null`)
            for all subscribed types. `value` + `expose` behave like `country`.
    """

    query: str
    engine: Literal["brave"] | Unset = "brave"
    fetch_size: int | Unset = 10
    timeout: int | Unset = 30
    extra_snippets: bool | Unset = True
    spellcheck: bool | Unset = False
    text_decorations: bool | Unset = True
    operators: bool | Unset = True
    ui_lang: str | Unset = "en-US"
    units: BraveSearchRequestUnitsType0 | None | Unset = UNSET
    summary: bool | Unset = True
    include_fetch_metadata: bool | Unset = False
    goggles: list[str] | str | Unset = UNSET
    country: None | str | Unset = UNSET
    freshness: None | str | Unset = UNSET
    search_lang: None | str | Unset = UNSET
    safesearch: BraveSearchRequestSafesearchType0 | None | Unset = UNSET
    result_filter: list[str] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        engine = self.engine

        fetch_size = self.fetch_size

        timeout = self.timeout

        extra_snippets = self.extra_snippets

        spellcheck = self.spellcheck

        text_decorations = self.text_decorations

        operators = self.operators

        ui_lang = self.ui_lang

        units: None | str | Unset
        if isinstance(self.units, Unset):
            units = UNSET
        elif isinstance(self.units, BraveSearchRequestUnitsType0):
            units = self.units.value
        else:
            units = self.units

        summary = self.summary

        include_fetch_metadata = self.include_fetch_metadata

        goggles: list[str] | str | Unset
        if isinstance(self.goggles, Unset):
            goggles = UNSET
        elif isinstance(self.goggles, list):
            goggles = self.goggles

        else:
            goggles = self.goggles

        country: None | str | Unset
        if isinstance(self.country, Unset):
            country = UNSET
        else:
            country = self.country

        freshness: None | str | Unset
        if isinstance(self.freshness, Unset):
            freshness = UNSET
        else:
            freshness = self.freshness

        search_lang: None | str | Unset
        if isinstance(self.search_lang, Unset):
            search_lang = UNSET
        else:
            search_lang = self.search_lang

        safesearch: None | str | Unset
        if isinstance(self.safesearch, Unset):
            safesearch = UNSET
        elif isinstance(self.safesearch, BraveSearchRequestSafesearchType0):
            safesearch = self.safesearch.value
        else:
            safesearch = self.safesearch

        result_filter: list[str] | None | Unset
        if isinstance(self.result_filter, Unset):
            result_filter = UNSET
        elif isinstance(self.result_filter, list):
            result_filter = self.result_filter

        else:
            result_filter = self.result_filter

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
        if extra_snippets is not UNSET:
            field_dict["extraSnippets"] = extra_snippets
        if spellcheck is not UNSET:
            field_dict["spellcheck"] = spellcheck
        if text_decorations is not UNSET:
            field_dict["textDecorations"] = text_decorations
        if operators is not UNSET:
            field_dict["operators"] = operators
        if ui_lang is not UNSET:
            field_dict["uiLang"] = ui_lang
        if units is not UNSET:
            field_dict["units"] = units
        if summary is not UNSET:
            field_dict["summary"] = summary
        if include_fetch_metadata is not UNSET:
            field_dict["includeFetchMetadata"] = include_fetch_metadata
        if goggles is not UNSET:
            field_dict["goggles"] = goggles
        if country is not UNSET:
            field_dict["country"] = country
        if freshness is not UNSET:
            field_dict["freshness"] = freshness
        if search_lang is not UNSET:
            field_dict["searchLang"] = search_lang
        if safesearch is not UNSET:
            field_dict["safesearch"] = safesearch
        if result_filter is not UNSET:
            field_dict["resultFilter"] = result_filter

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        engine = cast(Literal["brave"] | Unset, d.pop("engine", UNSET))
        if engine != "brave" and not isinstance(engine, Unset):
            raise ValueError(f"engine must match const 'brave', got '{engine}'")

        fetch_size = d.pop("fetchSize", UNSET)

        timeout = d.pop("timeout", UNSET)

        extra_snippets = d.pop("extraSnippets", UNSET)

        spellcheck = d.pop("spellcheck", UNSET)

        text_decorations = d.pop("textDecorations", UNSET)

        operators = d.pop("operators", UNSET)

        ui_lang = d.pop("uiLang", UNSET)

        def _parse_units(data: object) -> BraveSearchRequestUnitsType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                units_type_0 = BraveSearchRequestUnitsType0(data)

                return units_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(BraveSearchRequestUnitsType0 | None | Unset, data)

        units = _parse_units(d.pop("units", UNSET))

        summary = d.pop("summary", UNSET)

        include_fetch_metadata = d.pop("includeFetchMetadata", UNSET)

        def _parse_goggles(data: object) -> list[str] | str | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                goggles_type_1 = cast(list[str], data)

                return goggles_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | str | Unset, data)

        goggles = _parse_goggles(d.pop("goggles", UNSET))

        def _parse_country(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        country = _parse_country(d.pop("country", UNSET))

        def _parse_freshness(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        freshness = _parse_freshness(d.pop("freshness", UNSET))

        def _parse_search_lang(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        search_lang = _parse_search_lang(d.pop("searchLang", UNSET))

        def _parse_safesearch(
            data: object,
        ) -> BraveSearchRequestSafesearchType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                safesearch_type_0 = BraveSearchRequestSafesearchType0(data)

                return safesearch_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(BraveSearchRequestSafesearchType0 | None | Unset, data)

        safesearch = _parse_safesearch(d.pop("safesearch", UNSET))

        def _parse_result_filter(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                result_filter_type_0 = cast(list[str], data)

                return result_filter_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        result_filter = _parse_result_filter(d.pop("resultFilter", UNSET))

        brave_search_request = cls(
            query=query,
            engine=engine,
            fetch_size=fetch_size,
            timeout=timeout,
            extra_snippets=extra_snippets,
            spellcheck=spellcheck,
            text_decorations=text_decorations,
            operators=operators,
            ui_lang=ui_lang,
            units=units,
            summary=summary,
            include_fetch_metadata=include_fetch_metadata,
            goggles=goggles,
            country=country,
            freshness=freshness,
            search_lang=search_lang,
            safesearch=safesearch,
            result_filter=result_filter,
        )

        brave_search_request.additional_properties = d
        return brave_search_request

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
