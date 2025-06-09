"""
Request context protocol definition.

This protocol defines the interface that request contexts must implement,
enabling decoupling between the client layer and resource layer.
"""

from typing import Dict, Protocol


class RequestContextProtocol(Protocol):
    """
    Protocol defining the interface for request context implementations.

    This protocol enables the API resource layer to define its requirements
    without depending on specific client implementations.
    """

    def build_full_url(self, endpoint: str) -> str:
        """Build the complete URL for an API endpoint."""
        ...

    def build_headers(self, method: str) -> Dict[str, str]:
        """Build complete HTTP headers for API requests."""
        ...
