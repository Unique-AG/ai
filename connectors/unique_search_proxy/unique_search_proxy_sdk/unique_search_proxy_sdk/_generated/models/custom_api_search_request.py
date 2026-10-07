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

from ..models.custom_api_request_method import CustomApiRequestMethod
from ..types import UNSET, Unset

T = TypeVar("T", bound="CustomApiSearchRequest")


@_attrs_define
class CustomApiSearchRequest:
    r"""
    Attributes:
        query (str): Search query string
        engine (Literal['custom_api'] | Unset): Provider discriminator; must be `custom_api` for this config. Default:
            'custom_api'.
        api_endpoint (str | Unset): HTTP(S) endpoint called by Search Proxy. Default: 'https://api.example.com/search'.
        api_headers (str | Unset): JSON object containing headers sent to the custom API. Default: '{\\"Content-Type\\":
            \\"application/json\\"}'.
        api_additional_query_params (str | Unset): JSON object merged into the custom API query parameters. Default:
            '{}'.
        api_additional_body_params (str | Unset): JSON object merged into the custom API JSON body. Default: '{}'.
        api_request_method (CustomApiRequestMethod | Unset):
        timeout (int | Unset): Custom API request timeout in seconds. Default: 120.
    """

    query: str
    engine: Literal["custom_api"] | Unset = "custom_api"
    api_endpoint: str | Unset = "https://api.example.com/search"
    api_headers: str | Unset = '{\\"Content-Type\\": \\"application/json\\"}'
    api_additional_query_params: str | Unset = "{}"
    api_additional_body_params: str | Unset = "{}"
    api_request_method: CustomApiRequestMethod | Unset = UNSET
    timeout: int | Unset = 120
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        query = self.query

        engine = self.engine

        api_endpoint = self.api_endpoint

        api_headers = self.api_headers

        api_additional_query_params = self.api_additional_query_params

        api_additional_body_params = self.api_additional_body_params

        api_request_method: str | Unset = UNSET
        if not isinstance(self.api_request_method, Unset):
            api_request_method = self.api_request_method.value

        timeout = self.timeout

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "query": query,
            }
        )
        if engine is not UNSET:
            field_dict["engine"] = engine
        if api_endpoint is not UNSET:
            field_dict["apiEndpoint"] = api_endpoint
        if api_headers is not UNSET:
            field_dict["apiHeaders"] = api_headers
        if api_additional_query_params is not UNSET:
            field_dict["apiAdditionalQueryParams"] = api_additional_query_params
        if api_additional_body_params is not UNSET:
            field_dict["apiAdditionalBodyParams"] = api_additional_body_params
        if api_request_method is not UNSET:
            field_dict["apiRequestMethod"] = api_request_method
        if timeout is not UNSET:
            field_dict["timeout"] = timeout

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        query = d.pop("query")

        engine = cast(Literal["custom_api"] | Unset, d.pop("engine", UNSET))
        if engine != "custom_api" and not isinstance(engine, Unset):
            raise ValueError(f"engine must match const 'custom_api', got '{engine}'")

        api_endpoint = d.pop("apiEndpoint", UNSET)

        api_headers = d.pop("apiHeaders", UNSET)

        api_additional_query_params = d.pop("apiAdditionalQueryParams", UNSET)

        api_additional_body_params = d.pop("apiAdditionalBodyParams", UNSET)

        _api_request_method = d.pop("apiRequestMethod", UNSET)
        api_request_method: CustomApiRequestMethod | Unset
        if isinstance(_api_request_method, Unset):
            api_request_method = UNSET
        else:
            api_request_method = CustomApiRequestMethod(_api_request_method)

        timeout = d.pop("timeout", UNSET)

        custom_api_search_request = cls(
            query=query,
            engine=engine,
            api_endpoint=api_endpoint,
            api_headers=api_headers,
            api_additional_query_params=api_additional_query_params,
            api_additional_body_params=api_additional_body_params,
            api_request_method=api_request_method,
            timeout=timeout,
        )

        custom_api_search_request.additional_properties = d
        return custom_api_search_request

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
