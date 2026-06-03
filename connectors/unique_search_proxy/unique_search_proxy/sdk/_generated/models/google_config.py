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

from ..models.google_config_safe_search import GoogleConfigSafeSearch
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.exposable_ei import ExposableEI
    from ..models.exposable_str import ExposableStr


T = TypeVar("T", bound="GoogleConfig")


@_attrs_define
class GoogleConfig:
    """Single source of truth for Google deployment + derived request/LLM surfaces.

    Attributes:
        engine (Literal['google'] | Unset): Provider discriminator; must be `google` for this config. Default: 'google'.
        fetch_size (int | Unset): Default result count merged into each search request Default: 10.
        timeout (int | Unset): Request timeout in seconds Default: 30.
        search_engine_id (None | str | Unset): Google Programmable Search Engine ID (`cx`). Defaults from
            `GOOGLE_SEARCH_ENGINE_ID` when deployed. Not sent as a query parameter (resolved at runtime).
        safe (GoogleConfigSafeSearch | Unset): SafeSearch level for every search: `active` (default) or `off`. Applied
            on all requests unless the call body overrides it. Default: GoogleConfigSafeSearch.ACTIVE.
        gl (ExposableStr | Unset):
        hl (ExposableStr | Unset):
        lr (ExposableStr | Unset):
        date_restrict (ExposableStr | Unset):
        exact_terms (ExposableStr | Unset):
        exclude_terms (ExposableStr | Unset):
        file_type (ExposableStr | Unset):
        site_search (ExposableStr | Unset):
        site_search_filter (ExposableEI | Unset):
        sort (ExposableStr | Unset):
    """

    engine: Literal["google"] | Unset = "google"
    fetch_size: int | Unset = 10
    timeout: int | Unset = 30
    search_engine_id: None | str | Unset = UNSET
    safe: GoogleConfigSafeSearch | Unset = GoogleConfigSafeSearch.ACTIVE
    gl: ExposableStr | Unset = UNSET
    hl: ExposableStr | Unset = UNSET
    lr: ExposableStr | Unset = UNSET
    date_restrict: ExposableStr | Unset = UNSET
    exact_terms: ExposableStr | Unset = UNSET
    exclude_terms: ExposableStr | Unset = UNSET
    file_type: ExposableStr | Unset = UNSET
    site_search: ExposableStr | Unset = UNSET
    site_search_filter: ExposableEI | Unset = UNSET
    sort: ExposableStr | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
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

        gl: dict[str, Any] | Unset = UNSET
        if not isinstance(self.gl, Unset):
            gl = self.gl.to_dict()

        hl: dict[str, Any] | Unset = UNSET
        if not isinstance(self.hl, Unset):
            hl = self.hl.to_dict()

        lr: dict[str, Any] | Unset = UNSET
        if not isinstance(self.lr, Unset):
            lr = self.lr.to_dict()

        date_restrict: dict[str, Any] | Unset = UNSET
        if not isinstance(self.date_restrict, Unset):
            date_restrict = self.date_restrict.to_dict()

        exact_terms: dict[str, Any] | Unset = UNSET
        if not isinstance(self.exact_terms, Unset):
            exact_terms = self.exact_terms.to_dict()

        exclude_terms: dict[str, Any] | Unset = UNSET
        if not isinstance(self.exclude_terms, Unset):
            exclude_terms = self.exclude_terms.to_dict()

        file_type: dict[str, Any] | Unset = UNSET
        if not isinstance(self.file_type, Unset):
            file_type = self.file_type.to_dict()

        site_search: dict[str, Any] | Unset = UNSET
        if not isinstance(self.site_search, Unset):
            site_search = self.site_search.to_dict()

        site_search_filter: dict[str, Any] | Unset = UNSET
        if not isinstance(self.site_search_filter, Unset):
            site_search_filter = self.site_search_filter.to_dict()

        sort: dict[str, Any] | Unset = UNSET
        if not isinstance(self.sort, Unset):
            sort = self.sort.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
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
        from ..models.exposable_ei import ExposableEI
        from ..models.exposable_str import ExposableStr

        d = dict(src_dict)
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
        safe: GoogleConfigSafeSearch | Unset
        if isinstance(_safe, Unset):
            safe = UNSET
        else:
            safe = GoogleConfigSafeSearch(_safe)

        _gl = d.pop("gl", UNSET)
        gl: ExposableStr | Unset
        if isinstance(_gl, Unset):
            gl = UNSET
        else:
            gl = ExposableStr.from_dict(_gl)

        _hl = d.pop("hl", UNSET)
        hl: ExposableStr | Unset
        if isinstance(_hl, Unset):
            hl = UNSET
        else:
            hl = ExposableStr.from_dict(_hl)

        _lr = d.pop("lr", UNSET)
        lr: ExposableStr | Unset
        if isinstance(_lr, Unset):
            lr = UNSET
        else:
            lr = ExposableStr.from_dict(_lr)

        _date_restrict = d.pop("dateRestrict", UNSET)
        date_restrict: ExposableStr | Unset
        if isinstance(_date_restrict, Unset):
            date_restrict = UNSET
        else:
            date_restrict = ExposableStr.from_dict(_date_restrict)

        _exact_terms = d.pop("exactTerms", UNSET)
        exact_terms: ExposableStr | Unset
        if isinstance(_exact_terms, Unset):
            exact_terms = UNSET
        else:
            exact_terms = ExposableStr.from_dict(_exact_terms)

        _exclude_terms = d.pop("excludeTerms", UNSET)
        exclude_terms: ExposableStr | Unset
        if isinstance(_exclude_terms, Unset):
            exclude_terms = UNSET
        else:
            exclude_terms = ExposableStr.from_dict(_exclude_terms)

        _file_type = d.pop("fileType", UNSET)
        file_type: ExposableStr | Unset
        if isinstance(_file_type, Unset):
            file_type = UNSET
        else:
            file_type = ExposableStr.from_dict(_file_type)

        _site_search = d.pop("siteSearch", UNSET)
        site_search: ExposableStr | Unset
        if isinstance(_site_search, Unset):
            site_search = UNSET
        else:
            site_search = ExposableStr.from_dict(_site_search)

        _site_search_filter = d.pop("siteSearchFilter", UNSET)
        site_search_filter: ExposableEI | Unset
        if isinstance(_site_search_filter, Unset):
            site_search_filter = UNSET
        else:
            site_search_filter = ExposableEI.from_dict(_site_search_filter)

        _sort = d.pop("sort", UNSET)
        sort: ExposableStr | Unset
        if isinstance(_sort, Unset):
            sort = UNSET
        else:
            sort = ExposableStr.from_dict(_sort)

        google_config = cls(
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

        google_config.additional_properties = d
        return google_config

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
