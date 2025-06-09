"""HTTP Client Protocol definition."""

from typing import (
    Any,
    ClassVar,
    Dict,
    Mapping,
    Optional,
    Protocol,
    Tuple,
    runtime_checkable,
)

# Type aliases for better clarity
HTTPResponse = Tuple[bytes, int, Dict[str, str]]
HTTPHeaders = Mapping[str, str]
PostData = Optional[Dict[str, Any]]


@runtime_checkable
class HTTPClientProtocol(Protocol):
    """Protocol defining the interface for HTTP clients."""

    name: ClassVar[str]

    def request(
        self, method: str, url: str, headers: HTTPHeaders, post_data: PostData = None
    ) -> HTTPResponse:
        """Make a synchronous HTTP request."""
        ...

    def close(self) -> None:
        """Close the HTTP client and clean up resources."""
        ...

    async def request_async(
        self, method: str, url: str, headers: HTTPHeaders, post_data: PostData = None
    ) -> HTTPResponse:
        """Make an asynchronous HTTP request."""
        ...

    async def close_async(self) -> None:
        """Close the HTTP client asynchronously and clean up resources."""
        ...
