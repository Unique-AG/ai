from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.provider_json_schema_response import ProviderJsonSchemaResponse
from ...types import Response


def _get_kwargs(
    crawler_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/configuration/crawlers/{crawler_id}/json-schema".format(
            crawler_id=quote(str(crawler_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | ProviderJsonSchemaResponse | None:
    if response.status_code == 200:
        response_200 = ProviderJsonSchemaResponse.from_dict(response.json())

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
) -> Response[HTTPValidationError | ProviderJsonSchemaResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    crawler_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | ProviderJsonSchemaResponse]:
    """JSON Schema for one crawler config

    Args:
        crawler_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ProviderJsonSchemaResponse]
    """

    kwargs = _get_kwargs(
        crawler_id=crawler_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    crawler_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | ProviderJsonSchemaResponse | None:
    """JSON Schema for one crawler config

    Args:
        crawler_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ProviderJsonSchemaResponse
    """

    return sync_detailed(
        crawler_id=crawler_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    crawler_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | ProviderJsonSchemaResponse]:
    """JSON Schema for one crawler config

    Args:
        crawler_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ProviderJsonSchemaResponse]
    """

    kwargs = _get_kwargs(
        crawler_id=crawler_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    crawler_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | ProviderJsonSchemaResponse | None:
    """JSON Schema for one crawler config

    Args:
        crawler_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ProviderJsonSchemaResponse
    """

    return (
        await asyncio_detailed(
            crawler_id=crawler_id,
            client=client,
        )
    ).parsed
