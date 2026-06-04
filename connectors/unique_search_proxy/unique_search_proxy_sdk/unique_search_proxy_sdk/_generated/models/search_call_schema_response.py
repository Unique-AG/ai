from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.search_call_schema_response_callschema import (
        SearchCallSchemaResponseCallschema,
    )


T = TypeVar("T", bound="SearchCallSchemaResponse")


@_attrs_define
class SearchCallSchemaResponse:
    """
    Attributes:
        engine (str): Search engine id
        mode (str): Engine mode (e.g. standard) for observability and tooling
        snippet_only (bool): When true, search hits are snippet-only; use POST /v1/crawl for bodies
        call_schema (SearchCallSchemaResponseCallschema): JSON Schema for the engine call model on POST /v1/search
    """

    engine: str
    mode: str
    snippet_only: bool
    call_schema: SearchCallSchemaResponseCallschema
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        engine = self.engine

        mode = self.mode

        snippet_only = self.snippet_only

        call_schema = self.call_schema.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "engine": engine,
                "mode": mode,
                "snippetOnly": snippet_only,
                "callSchema": call_schema,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.search_call_schema_response_callschema import (
            SearchCallSchemaResponseCallschema,
        )

        d = dict(src_dict)
        engine = d.pop("engine")

        mode = d.pop("mode")

        snippet_only = d.pop("snippetOnly")

        call_schema = SearchCallSchemaResponseCallschema.from_dict(d.pop("callSchema"))

        search_call_schema_response = cls(
            engine=engine,
            mode=mode,
            snippet_only=snippet_only,
            call_schema=call_schema,
        )

        search_call_schema_response.additional_properties = d
        return search_call_schema_response

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
