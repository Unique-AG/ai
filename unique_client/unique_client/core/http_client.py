"""
HTTP Client module - now using factory pattern with separate client implementations.

This module provides a clean interface to HTTP clients that are dynamically loaded
based on available dependencies.
"""

from unique_client.core.http_clients import (
    HTTPClientProtocol,
    HTTPHeaders,
    HTTPResponse,
    PostData,
    get_async_client,
    get_default_client,
)


# Legacy function names for backward compatibility
def new_default_http_client(*args, **kwargs) -> HTTPClientProtocol:
    """Create a new default HTTP client instance."""
    return get_default_client(*args, **kwargs)


def new_http_client_async_fallback(*args, **kwargs) -> HTTPClientProtocol:
    """Create a new async-capable HTTP client instance."""
    async_client = get_async_client(*args, **kwargs)
    if async_client:
        return async_client
    return get_default_client(*args, **kwargs)


# Re-export everything for backward compatibility
__all__ = [
    "HTTPClientProtocol",
    "HTTPResponse",
    "HTTPHeaders",
    "PostData",
    "new_default_http_client",
    "new_http_client_async_fallback",
    "get_default_client",
    "get_async_client",
]
