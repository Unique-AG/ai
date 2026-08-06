"""Backward-compatible import path for feature-flag cache users."""

from unique_toolkit._common.async_ttl_cache import AsyncTTLCache

__all__ = ["AsyncTTLCache"]
