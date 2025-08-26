"""
Core infrastructure for the Unique SDK v2.

This layer contains shared infrastructure components used by other layers.
"""

from unique_client.core.base_resource import APIResource
from unique_client.core.errors import (
    AuthenticationError,
    InvalidRequestError,
    UniqueError,
)
from unique_client.core.requestor import APIRequestor
from unique_client.core.utils import retry_on_error

__all__ = [
    "APIResource",
    "APIRequestor",
    "AuthenticationError",
    "InvalidRequestError",
    "UniqueError",
    "retry_on_error",
]
