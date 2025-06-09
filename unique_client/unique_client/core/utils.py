"""
Utility functions for the Unique SDK v2.

This module provides utility functions for logging, serialization, and retries.
"""

import asyncio
import random
import time
from functools import wraps
from typing import Any, Callable, List

from unique_client.core.errors import APIError


def _console_log_level():
    # TODO: Import log from main module to avoid circular import
    import unique_client

    return getattr(unique_client, "log", None)


def log_debug(message, **params):
    if _console_log_level() == "debug":
        print(f"DEBUG: {message}", params, flush=True)


def log_info(message, **params):
    if _console_log_level() in ["debug", "info"]:
        print(f"INFO: {message}", params, flush=True)


def logfmt(props):
    def fmt(key, val):
        # Handle case where val is a bytes or bytesarray
        if hasattr(val, "decode"):
            val = val.decode("utf-8")
        # Check if val is a string-like object and needs to be encoded
        if not isinstance(val, str):
            val = str(val)

        if " " in val:
            val = repr(val)
        # Key should always be a string
        if not isinstance(key, str):
            key = str(key)

        return "{key}={val}".format(key=key, val=val)

    return " ".join([fmt(key, val) for key, val in sorted(props.items())])


def retry_on_error(
    error_messages: List[str],
    max_retries: int = 3,
    initial_delay: int = 1,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    error_class=APIError,
    should_retry_5xx=False,
):
    """
    Decorator to retry functions on specific errors with exponential backoff.

    Args:
        error_messages: List of error message patterns to retry on
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay between retries
        jitter: Add random jitter to delay
        error_class: Exception class to catch
        should_retry_5xx: Whether to retry on 5xx HTTP errors
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except error_class as e:
                    last_exception = e
                    should_retry = False

                    # Check if error message matches retry patterns
                    error_msg = str(e).lower()
                    for pattern in error_messages:
                        if pattern.lower() in error_msg:
                            should_retry = True
                            break

                    # Check for 5xx errors if enabled
                    if (
                        should_retry_5xx
                        and hasattr(e, "http_status")
                        and e.http_status
                        and 500 <= e.http_status < 600
                    ):
                        should_retry = True

                    if not should_retry or attempt == max_retries - 1:
                        break

                    # Calculate delay with jitter
                    actual_delay = delay
                    if jitter:
                        actual_delay *= 0.5 + random.random() * 0.5

                    await asyncio.sleep(actual_delay)
                    delay *= backoff_factor

            # If we get here, all retries failed
            raise error_class(
                f"Failed after {max_retries} attempts"
            ) from last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except error_class as e:
                    last_exception = e
                    should_retry = False

                    # Check if error message matches retry patterns
                    error_msg = str(e).lower()
                    for pattern in error_messages:
                        if pattern.lower() in error_msg:
                            should_retry = True
                            break

                    # Check for 5xx errors if enabled
                    if (
                        should_retry_5xx
                        and hasattr(e, "http_status")
                        and e.http_status
                        and 500 <= e.http_status < 600
                    ):
                        should_retry = True

                    if not should_retry or attempt == max_retries - 1:
                        break

                    # Calculate delay with jitter
                    actual_delay = delay
                    if jitter:
                        actual_delay *= 0.5 + random.random() * 0.5

                    time.sleep(actual_delay)
                    delay *= backoff_factor

            # If we get here, all retries failed
            raise error_class(
                f"Failed after {max_retries} attempts"
            ) from last_exception

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
