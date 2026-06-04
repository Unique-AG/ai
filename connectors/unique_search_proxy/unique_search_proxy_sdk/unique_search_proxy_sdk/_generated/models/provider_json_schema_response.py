from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.provider_json_schema_response_jsonschema import (
        ProviderJsonSchemaResponseJsonschema,
    )


T = TypeVar("T", bound="ProviderJsonSchemaResponse")


@_attrs_define
class ProviderJsonSchemaResponse:
    """
    Attributes:
        json_schema (ProviderJsonSchemaResponseJsonschema): JSON Schema for provider deployment configuration
        provider_id (None | str | Unset): Set when the schema is for a single provider
    """

    json_schema: ProviderJsonSchemaResponseJsonschema
    provider_id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        json_schema = self.json_schema.to_dict()

        provider_id: None | str | Unset
        if isinstance(self.provider_id, Unset):
            provider_id = UNSET
        else:
            provider_id = self.provider_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "jsonSchema": json_schema,
            }
        )
        if provider_id is not UNSET:
            field_dict["providerId"] = provider_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.provider_json_schema_response_jsonschema import (
            ProviderJsonSchemaResponseJsonschema,
        )

        d = dict(src_dict)
        json_schema = ProviderJsonSchemaResponseJsonschema.from_dict(
            d.pop("jsonSchema")
        )

        def _parse_provider_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        provider_id = _parse_provider_id(d.pop("providerId", UNSET))

        provider_json_schema_response = cls(
            json_schema=json_schema,
            provider_id=provider_id,
        )

        provider_json_schema_response.additional_properties = d
        return provider_json_schema_response

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
