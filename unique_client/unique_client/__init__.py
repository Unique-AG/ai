"""
Unique SDK v2 - Modern Python SDK for the Unique API

This is the main SDK module that provides clean, modern interfaces
for interacting with the Unique API.
"""

from unique_client._version import __version__
from unique_client.unique_client import UniqueClient

__all__ = ["UniqueClient", "__version__"]
