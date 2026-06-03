from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.google_config import GoogleConfig
from ...models.http_validation_error import HTTPValidationError
from ...models.search_call_schema_response import SearchCallSchemaResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    engine_id: str,
    *,
    body: GoogleConfig,
    strict: bool | Unset = True,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["strict"] = strict

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/configuration/search-engines/{engine_id}/call-schema".format(
            engine_id=quote(str(engine_id), safe=""),
        ),
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | SearchCallSchemaResponse | None:
    if response.status_code == 200:
        response_200 = SearchCallSchemaResponse.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | SearchCallSchemaResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    engine_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: GoogleConfig,
    strict: bool | Unset = True,
) -> Response[HTTPValidationError | SearchCallSchemaResponse]:
    """JSON Schema for POST /v1/search from deployment config

    Args:
        engine_id (str):
        strict (bool | Unset): When true (default), the call schema marks every exposed field as
            required with no defaults (for strict LLM JSON generation). When false, optional provider
            knobs keep nullable types and defaults. Default: True.
        body (GoogleConfig): Single source of truth for Google deployment + derived request/LLM
            surfaces.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchCallSchemaResponse]
    """

    kwargs = _get_kwargs(
        engine_id=engine_id,
        body=body,
        strict=strict,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    engine_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: GoogleConfig,
    strict: bool | Unset = True,
) -> HTTPValidationError | SearchCallSchemaResponse | None:
    """JSON Schema for POST /v1/search from deployment config

    Args:
        engine_id (str):
        strict (bool | Unset): When true (default), the call schema marks every exposed field as
            required with no defaults (for strict LLM JSON generation). When false, optional provider
            knobs keep nullable types and defaults. Default: True.
        body (GoogleConfig): Single source of truth for Google deployment + derived request/LLM
            surfaces.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchCallSchemaResponse
    """

    return sync_detailed(
        engine_id=engine_id,
        client=client,
        body=body,
        strict=strict,
    ).parsed


async def asyncio_detailed(
    engine_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: GoogleConfig,
    strict: bool | Unset = True,
) -> Response[HTTPValidationError | SearchCallSchemaResponse]:
    """JSON Schema for POST /v1/search from deployment config

    Args:
        engine_id (str):
        strict (bool | Unset): When true (default), the call schema marks every exposed field as
            required with no defaults (for strict LLM JSON generation). When false, optional provider
            knobs keep nullable types and defaults. Default: True.
        body (GoogleConfig): Single source of truth for Google deployment + derived request/LLM
            surfaces.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchCallSchemaResponse]
    """

    kwargs = _get_kwargs(
        engine_id=engine_id,
        body=body,
        strict=strict,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    engine_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: GoogleConfig,
    strict: bool | Unset = True,
) -> HTTPValidationError | SearchCallSchemaResponse | None:
    """JSON Schema for POST /v1/search from deployment config

    Args:
        engine_id (str):
        strict (bool | Unset): When true (default), the call schema marks every exposed field as
            required with no defaults (for strict LLM JSON generation). When false, optional provider
            knobs keep nullable types and defaults. Default: True.
        body (GoogleConfig): Single source of truth for Google deployment + derived request/LLM
            surfaces.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchCallSchemaResponse
    """

    return (
        await asyncio_detailed(
            engine_id=engine_id,
            client=client,
            body=body,
            strict=strict,
        )
    ).parsed
