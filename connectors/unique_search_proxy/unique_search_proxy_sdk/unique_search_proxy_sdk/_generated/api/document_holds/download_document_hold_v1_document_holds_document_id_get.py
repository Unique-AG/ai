from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    document_id: str,
    *,
    authorization: None | str | Unset = UNSET,
    x_unique_company_id: str | Unset = "local",
    x_unique_user_id: str | Unset = "local",
    x_unique_chat_id: str | Unset = "local",
    x_unique_entry_point: str | Unset = "unknown",
    x_unique_message_id: None | str | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    if not isinstance(authorization, Unset):
        headers["authorization"] = authorization

    if not isinstance(x_unique_company_id, Unset):
        headers["x-unique-company-id"] = x_unique_company_id

    if not isinstance(x_unique_user_id, Unset):
        headers["x-unique-user-id"] = x_unique_user_id

    if not isinstance(x_unique_chat_id, Unset):
        headers["x-unique-chat-id"] = x_unique_chat_id

    if not isinstance(x_unique_entry_point, Unset):
        headers["x-unique-entry-point"] = x_unique_entry_point

    if not isinstance(x_unique_message_id, Unset):
        headers["x-unique-message-id"] = x_unique_message_id

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/document-holds/{document_id}".format(
            document_id=quote(str(document_id), safe=""),
        ),
    }

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = cast(Any, None)
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
) -> Response[Any | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    document_id: str,
    *,
    client: AuthenticatedClient | Client,
    authorization: None | str | Unset = UNSET,
    x_unique_company_id: str | Unset = "local",
    x_unique_user_id: str | Unset = "local",
    x_unique_chat_id: str | Unset = "local",
    x_unique_entry_point: str | Unset = "unknown",
    x_unique_message_id: None | str | Unset = UNSET,
) -> Response[Any | HTTPValidationError]:
    """Download a held document

     Stream and consume a pod-local document hold created when a crawled PDF exceeded the inline
    extraction budget. Requires ``Authorization: Bearer <one-time-token>`` from the crawl handle.

    Args:
        document_id (str):
        authorization (None | str | Unset):
        x_unique_company_id (str | Unset): Tenant company identifier. Default: 'local'.
        x_unique_user_id (str | Unset): Tenant user identifier. Default: 'local'.
        x_unique_chat_id (str | Unset): Tenant chat or session identifier. Default: 'local'.
        x_unique_entry_point (str | Unset): Service where the search entered the platform.
            Default: 'unknown'.
        x_unique_message_id (None | str | Unset): Message identifier, reserved for analytics.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        document_id=document_id,
        authorization=authorization,
        x_unique_company_id=x_unique_company_id,
        x_unique_user_id=x_unique_user_id,
        x_unique_chat_id=x_unique_chat_id,
        x_unique_entry_point=x_unique_entry_point,
        x_unique_message_id=x_unique_message_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    document_id: str,
    *,
    client: AuthenticatedClient | Client,
    authorization: None | str | Unset = UNSET,
    x_unique_company_id: str | Unset = "local",
    x_unique_user_id: str | Unset = "local",
    x_unique_chat_id: str | Unset = "local",
    x_unique_entry_point: str | Unset = "unknown",
    x_unique_message_id: None | str | Unset = UNSET,
) -> Any | HTTPValidationError | None:
    """Download a held document

     Stream and consume a pod-local document hold created when a crawled PDF exceeded the inline
    extraction budget. Requires ``Authorization: Bearer <one-time-token>`` from the crawl handle.

    Args:
        document_id (str):
        authorization (None | str | Unset):
        x_unique_company_id (str | Unset): Tenant company identifier. Default: 'local'.
        x_unique_user_id (str | Unset): Tenant user identifier. Default: 'local'.
        x_unique_chat_id (str | Unset): Tenant chat or session identifier. Default: 'local'.
        x_unique_entry_point (str | Unset): Service where the search entered the platform.
            Default: 'unknown'.
        x_unique_message_id (None | str | Unset): Message identifier, reserved for analytics.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
    """

    return sync_detailed(
        document_id=document_id,
        client=client,
        authorization=authorization,
        x_unique_company_id=x_unique_company_id,
        x_unique_user_id=x_unique_user_id,
        x_unique_chat_id=x_unique_chat_id,
        x_unique_entry_point=x_unique_entry_point,
        x_unique_message_id=x_unique_message_id,
    ).parsed


async def asyncio_detailed(
    document_id: str,
    *,
    client: AuthenticatedClient | Client,
    authorization: None | str | Unset = UNSET,
    x_unique_company_id: str | Unset = "local",
    x_unique_user_id: str | Unset = "local",
    x_unique_chat_id: str | Unset = "local",
    x_unique_entry_point: str | Unset = "unknown",
    x_unique_message_id: None | str | Unset = UNSET,
) -> Response[Any | HTTPValidationError]:
    """Download a held document

     Stream and consume a pod-local document hold created when a crawled PDF exceeded the inline
    extraction budget. Requires ``Authorization: Bearer <one-time-token>`` from the crawl handle.

    Args:
        document_id (str):
        authorization (None | str | Unset):
        x_unique_company_id (str | Unset): Tenant company identifier. Default: 'local'.
        x_unique_user_id (str | Unset): Tenant user identifier. Default: 'local'.
        x_unique_chat_id (str | Unset): Tenant chat or session identifier. Default: 'local'.
        x_unique_entry_point (str | Unset): Service where the search entered the platform.
            Default: 'unknown'.
        x_unique_message_id (None | str | Unset): Message identifier, reserved for analytics.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        document_id=document_id,
        authorization=authorization,
        x_unique_company_id=x_unique_company_id,
        x_unique_user_id=x_unique_user_id,
        x_unique_chat_id=x_unique_chat_id,
        x_unique_entry_point=x_unique_entry_point,
        x_unique_message_id=x_unique_message_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    document_id: str,
    *,
    client: AuthenticatedClient | Client,
    authorization: None | str | Unset = UNSET,
    x_unique_company_id: str | Unset = "local",
    x_unique_user_id: str | Unset = "local",
    x_unique_chat_id: str | Unset = "local",
    x_unique_entry_point: str | Unset = "unknown",
    x_unique_message_id: None | str | Unset = UNSET,
) -> Any | HTTPValidationError | None:
    """Download a held document

     Stream and consume a pod-local document hold created when a crawled PDF exceeded the inline
    extraction budget. Requires ``Authorization: Bearer <one-time-token>`` from the crawl handle.

    Args:
        document_id (str):
        authorization (None | str | Unset):
        x_unique_company_id (str | Unset): Tenant company identifier. Default: 'local'.
        x_unique_user_id (str | Unset): Tenant user identifier. Default: 'local'.
        x_unique_chat_id (str | Unset): Tenant chat or session identifier. Default: 'local'.
        x_unique_entry_point (str | Unset): Service where the search entered the platform.
            Default: 'unknown'.
        x_unique_message_id (None | str | Unset): Message identifier, reserved for analytics.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            document_id=document_id,
            client=client,
            authorization=authorization,
            x_unique_company_id=x_unique_company_id,
            x_unique_user_id=x_unique_user_id,
            x_unique_chat_id=x_unique_chat_id,
            x_unique_entry_point=x_unique_entry_point,
            x_unique_message_id=x_unique_message_id,
        )
    ).parsed
