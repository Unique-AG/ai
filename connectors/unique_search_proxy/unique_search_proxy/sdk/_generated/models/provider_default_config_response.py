from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.provider_default_config_response_defaultconfig import (
        ProviderDefaultConfigResponseDefaultconfig,
    )


T = TypeVar("T", bound="ProviderDefaultConfigResponse")


@_attrs_define
class ProviderDefaultConfigResponse:
    """
    Attributes:
        provider_id (str):
        default_config (ProviderDefaultConfigResponseDefaultconfig): Default deployment config (camelCase keys)
    """

    provider_id: str
    default_config: ProviderDefaultConfigResponseDefaultconfig
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        provider_id = self.provider_id

        default_config = self.default_config.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "providerId": provider_id,
                "defaultConfig": default_config,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.provider_default_config_response_defaultconfig import (
            ProviderDefaultConfigResponseDefaultconfig,
        )

        d = dict(src_dict)
        provider_id = d.pop("providerId")

        default_config = ProviderDefaultConfigResponseDefaultconfig.from_dict(
            d.pop("defaultConfig")
        )

        provider_default_config_response = cls(
            provider_id=provider_id,
            default_config=default_config,
        )

        provider_default_config_response.additional_properties = d
        return provider_default_config_response

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
