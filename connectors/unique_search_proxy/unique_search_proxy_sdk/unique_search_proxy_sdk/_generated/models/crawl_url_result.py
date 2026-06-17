from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.per_url_error import PerUrlError


T = TypeVar("T", bound="CrawlUrlResult")


@_attrs_define
class CrawlUrlResult:
    """
    Attributes:
        url (str):
        content (None | str | Unset): Markdown extracted from HTML responses; null when unprocessed
        content_type (None | str | Unset): Response Content-Type (media type only, parameters stripped)
        error (None | PerUrlError | Unset):
        raw (Any | None | Unset): Upstream provider response for this URL (JSON object or text wrapper); included on
            success and on per-URL failures for debugging
    """

    url: str
    content: None | str | Unset = UNSET
    content_type: None | str | Unset = UNSET
    error: None | PerUrlError | Unset = UNSET
    raw: Any | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.per_url_error import PerUrlError

        url = self.url

        content: None | str | Unset
        if isinstance(self.content, Unset):
            content = UNSET
        else:
            content = self.content

        content_type: None | str | Unset
        if isinstance(self.content_type, Unset):
            content_type = UNSET
        else:
            content_type = self.content_type

        error: dict[str, Any] | None | Unset
        if isinstance(self.error, Unset):
            error = UNSET
        elif isinstance(self.error, PerUrlError):
            error = self.error.to_dict()
        else:
            error = self.error

        raw: Any | None | Unset
        if isinstance(self.raw, Unset):
            raw = UNSET
        else:
            raw = self.raw

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "url": url,
            }
        )
        if content is not UNSET:
            field_dict["content"] = content
        if content_type is not UNSET:
            field_dict["contentType"] = content_type
        if error is not UNSET:
            field_dict["error"] = error
        if raw is not UNSET:
            field_dict["raw"] = raw

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.per_url_error import PerUrlError

        d = dict(src_dict)
        url = d.pop("url")

        def _parse_content(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        content = _parse_content(d.pop("content", UNSET))

        def _parse_content_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        content_type = _parse_content_type(d.pop("contentType", UNSET))

        def _parse_error(data: object) -> None | PerUrlError | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                error_type_0 = PerUrlError.from_dict(data)

                return error_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | PerUrlError | Unset, data)

        error = _parse_error(d.pop("error", UNSET))

        def _parse_raw(data: object) -> Any | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Any | None | Unset, data)

        raw = _parse_raw(d.pop("raw", UNSET))

        crawl_url_result = cls(
            url=url,
            content=content,
            content_type=content_type,
            error=error,
            raw=raw,
        )

        crawl_url_result.additional_properties = d
        return crawl_url_result

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
