from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="AnswerSpanCitation")


@_attrs_define
class AnswerSpanCitation:
    """A source cited at a specific span of the answer text.

    Grounding with Bing Search reports these as ``url_citation`` annotations:
    the agent writes a marker such as ``【4:0†source】`` into its answer, and
    Foundry attaches the source to that marker's character span.

        Attributes:
            url (str): URL of the cited source
            marker (str): Answer text between start_index and end_index
            start_index (int): Character offset in the answer where the marker starts
            end_index (int): Character offset in the answer just past the marker
            title (None | str | Unset): Title of the cited source
            output_item_id (None | str | Unset): Output item the citation is attached to, if the provider reports one
    """

    url: str
    marker: str
    start_index: int
    end_index: int
    title: None | str | Unset = UNSET
    output_item_id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        url = self.url

        marker = self.marker

        start_index = self.start_index

        end_index = self.end_index

        title: None | str | Unset
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        output_item_id: None | str | Unset
        if isinstance(self.output_item_id, Unset):
            output_item_id = UNSET
        else:
            output_item_id = self.output_item_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "url": url,
                "marker": marker,
                "startIndex": start_index,
                "endIndex": end_index,
            }
        )
        if title is not UNSET:
            field_dict["title"] = title
        if output_item_id is not UNSET:
            field_dict["outputItemId"] = output_item_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        url = d.pop("url")

        marker = d.pop("marker")

        start_index = d.pop("startIndex")

        end_index = d.pop("endIndex")

        def _parse_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        title = _parse_title(d.pop("title", UNSET))

        def _parse_output_item_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        output_item_id = _parse_output_item_id(d.pop("outputItemId", UNSET))

        answer_span_citation = cls(
            url=url,
            marker=marker,
            start_index=start_index,
            end_index=end_index,
            title=title,
            output_item_id=output_item_id,
        )

        answer_span_citation.additional_properties = d
        return answer_span_citation

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
