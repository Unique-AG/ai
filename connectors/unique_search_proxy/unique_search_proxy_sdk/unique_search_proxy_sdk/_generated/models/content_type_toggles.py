from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ContentTypeToggles")


@_attrs_define
class ContentTypeToggles:
    """Per-type activation flags for basic-crawler content processing.

    Attributes:
        html (bool | Unset): Process ``text/html`` responses into the content field Default: False.
        xhtml (bool | Unset): Process ``application/xhtml+xml`` responses into the content field Default: False.
        plain_text (bool | Unset): Process ``text/plain`` responses into the content field Default: False.
        markdown (bool | Unset): Process ``text/markdown`` responses into the content field Default: False.
        pdf (bool | Unset): Process ``application/pdf`` responses into the content field Default: False.
    """

    html: bool | Unset = False
    xhtml: bool | Unset = False
    plain_text: bool | Unset = False
    markdown: bool | Unset = False
    pdf: bool | Unset = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        html = self.html

        xhtml = self.xhtml

        plain_text = self.plain_text

        markdown = self.markdown

        pdf = self.pdf

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if html is not UNSET:
            field_dict["html"] = html
        if xhtml is not UNSET:
            field_dict["xhtml"] = xhtml
        if plain_text is not UNSET:
            field_dict["plainText"] = plain_text
        if markdown is not UNSET:
            field_dict["markdown"] = markdown
        if pdf is not UNSET:
            field_dict["pdf"] = pdf

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        html = d.pop("html", UNSET)

        xhtml = d.pop("xhtml", UNSET)

        plain_text = d.pop("plainText", UNSET)

        markdown = d.pop("markdown", UNSET)

        pdf = d.pop("pdf", UNSET)

        content_type_toggles = cls(
            html=html,
            xhtml=xhtml,
            plain_text=plain_text,
            markdown=markdown,
            pdf=pdf,
        )

        content_type_toggles.additional_properties = d
        return content_type_toggles

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
