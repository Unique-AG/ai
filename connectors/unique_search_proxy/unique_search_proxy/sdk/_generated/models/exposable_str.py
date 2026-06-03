from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ExposableStr")


@_attrs_define
class ExposableStr:
    """
    Attributes:
        expose (bool): When true, this parameter is included on the LLM call JSON Schema.
        value (None | str): Admin default merged into each search when not ``None``.
    """

    expose: bool
    value: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        expose = self.expose

        value: None | str
        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "expose": expose,
                "value": value,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        expose = d.pop("expose")

        def _parse_value(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        value = _parse_value(d.pop("value"))

        exposable_str = cls(
            expose=expose,
            value=value,
        )

        exposable_str.additional_properties = d
        return exposable_str

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
