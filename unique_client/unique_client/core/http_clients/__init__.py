"""HTTP Client implementations package."""

from unique_client.core.http_clients.factory import (
    ClientInfo,
    HTTPClientType,
    get_async_client,
    get_client_by_name,
    get_client_by_type,
    get_default_client,
)
from unique_client.core.http_clients.protocol import (
    HTTPClientProtocol,
    HTTPHeaders,
    HTTPResponse,
    PostData,
)

__all__ = [
    "HTTPClientProtocol",
    "HTTPResponse",
    "HTTPHeaders",
    "PostData",
    "get_default_client",
    "get_async_client",
    "get_client_by_name",
    "get_client_by_type",
    "HTTPClientType",
    "ClientInfo",
]
