from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.brave_search_request import BraveSearchRequest
from ...models.google_search_request import GoogleSearchRequest
from ...models.http_validation_error import HTTPValidationError
from ...models.perplexity_search_request import PerplexitySearchRequest
from ...models.search_response import SearchResponse
from ...types import Response, Unset


def _get_kwargs(
    *,
    body: BraveSearchRequest | GoogleSearchRequest | PerplexitySearchRequest,
    x_unique_company_id: str | Unset = "local",
    x_unique_user_id: str | Unset = "local",
    x_unique_chat_id: str | Unset = "local",
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(x_unique_company_id, Unset):
        headers["x-unique-company-id"] = x_unique_company_id

    if not isinstance(x_unique_user_id, Unset):
        headers["x-unique-user-id"] = x_unique_user_id

    if not isinstance(x_unique_chat_id, Unset):
        headers["x-unique-chat-id"] = x_unique_chat_id

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/search",
    }

    if isinstance(body, GoogleSearchRequest):
        _kwargs["json"] = body.to_dict()
    elif isinstance(body, BraveSearchRequest):
        _kwargs["json"] = body.to_dict()
    else:
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | SearchResponse | None:
    if response.status_code == 200:
        response_200 = SearchResponse.from_dict(response.json())

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
) -> Response[HTTPValidationError | SearchResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: BraveSearchRequest | GoogleSearchRequest | PerplexitySearchRequest,
    x_unique_company_id: str | Unset = "local",
    x_unique_user_id: str | Unset = "local",
    x_unique_chat_id: str | Unset = "local",
) -> Response[HTTPValidationError | SearchResponse]:
    """Run a search engine with a typed call payload

    Args:
        x_unique_company_id (str | Unset): Tenant company identifier. Default: 'local'.
        x_unique_user_id (str | Unset): Tenant user identifier. Default: 'local'.
        x_unique_chat_id (str | Unset): Tenant chat or session identifier. Default: 'local'.
        body (BraveSearchRequest | GoogleSearchRequest | PerplexitySearchRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        x_unique_company_id=x_unique_company_id,
        x_unique_user_id=x_unique_user_id,
        x_unique_chat_id=x_unique_chat_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: BraveSearchRequest | GoogleSearchRequest | PerplexitySearchRequest,
    x_unique_company_id: str | Unset = "local",
    x_unique_user_id: str | Unset = "local",
    x_unique_chat_id: str | Unset = "local",
) -> HTTPValidationError | SearchResponse | None:
    """Run a search engine with a typed call payload

    Args:
        x_unique_company_id (str | Unset): Tenant company identifier. Default: 'local'.
        x_unique_user_id (str | Unset): Tenant user identifier. Default: 'local'.
        x_unique_chat_id (str | Unset): Tenant chat or session identifier. Default: 'local'.
        body (BraveSearchRequest | GoogleSearchRequest | PerplexitySearchRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchResponse
    """

    return sync_detailed(
        client=client,
        body=body,
        x_unique_company_id=x_unique_company_id,
        x_unique_user_id=x_unique_user_id,
        x_unique_chat_id=x_unique_chat_id,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: BraveSearchRequest | GoogleSearchRequest | PerplexitySearchRequest,
    x_unique_company_id: str | Unset = "local",
    x_unique_user_id: str | Unset = "local",
    x_unique_chat_id: str | Unset = "local",
) -> Response[HTTPValidationError | SearchResponse]:
    """Run a search engine with a typed call payload

    Args:
        x_unique_company_id (str | Unset): Tenant company identifier. Default: 'local'.
        x_unique_user_id (str | Unset): Tenant user identifier. Default: 'local'.
        x_unique_chat_id (str | Unset): Tenant chat or session identifier. Default: 'local'.
        body (BraveSearchRequest | GoogleSearchRequest | PerplexitySearchRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        x_unique_company_id=x_unique_company_id,
        x_unique_user_id=x_unique_user_id,
        x_unique_chat_id=x_unique_chat_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: BraveSearchRequest | GoogleSearchRequest | PerplexitySearchRequest,
    x_unique_company_id: str | Unset = "local",
    x_unique_user_id: str | Unset = "local",
    x_unique_chat_id: str | Unset = "local",
) -> HTTPValidationError | SearchResponse | None:
    """Run a search engine with a typed call payload

    Args:
        x_unique_company_id (str | Unset): Tenant company identifier. Default: 'local'.
        x_unique_user_id (str | Unset): Tenant user identifier. Default: 'local'.
        x_unique_chat_id (str | Unset): Tenant chat or session identifier. Default: 'local'.
        body (BraveSearchRequest | GoogleSearchRequest | PerplexitySearchRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            x_unique_company_id=x_unique_company_id,
            x_unique_user_id=x_unique_user_id,
            x_unique_chat_id=x_unique_chat_id,
        )
    ).parsed
